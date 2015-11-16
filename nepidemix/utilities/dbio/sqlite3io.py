"""
sqlite3 IO
==========

Utility functions to extract data from NepidemiX sqlite3 output databases.
"""
__author__ =  "Lukas Ahrenberg (lukas@ahrenberg.se)"

__license__ = "Modified BSD License"


import sys

NODE_EVENT_TABLE_NAME = "node_event"
NODE_EVENT_TABLE_SRC_STATE_COL = "src_state"
NODE_EVENT_TABLE_DST_STATE_COL = "dst_state"
NODE_STATE_TABLE_NAME = "node_state"

def get_flow(db_connection, state, time_min = None, time_max = None):
    """
    Return state event array and time step.

    Parameters
    ----------
    
    db_connection : sqlite3.Connection
    
    state : dictionary
       Dictionary of attributes with possible values. They keys should be names
       of attributes, and the values should be a 
       set (or an iterable) containing all possible values for the corresponding
       attribute. E.g. {"'disease'" : ["'acute'","'latent'"], "'age_group'" : ("'B'",)} will
       select all states where the 'disease' state is either the string 'acute'
       or the string 'latent', and where the attribute 'age_group' must be the
       string 'B'. Note that string values must be 'escaped'. 
       If the node/edge has any other associated attributes they can have any 
       value.

    time_min : float or None
       If not None, only event with time stamps greater or equal to this number 
       are selected.

    time_max : float or None
       If not None, only event with time stamps strictly less than this number 
       are selected.
    """
    # Open connection to db.
    cur = db_connection.cursor()

    # Need to make sure every state variable is a set (and thus iterable)
    # if a type error is cast, we'll assume the object is a unit and create a
    # set of only that object.
    # for k,v in state.items():
    #     try:
    #         state[k] = set(v)
    #     except TypeError:
    #         state[k] = set([v])

    # Node event table conditions added to this list.
    nevent_where_cond_list = []
    if time_min != None:
        nevent_where_cond_list.append("time >= {0}".format(time_min))
    if time_max != None:
        nevent_where_cond_list.append("time < {0}".format(time_max))

    # Node state table conditions added to this list.
    nstate_where_cond_list = []
    # The state options as a string;
    # Explanation: Strings on the form of <key> IN (<value1>, <value2>, ...)
    nstate_where_cond_list.extend(["{0} IN ({1})".format(k, ",".join(v))\
                                   for k,v in state.iteritems()])

    # Helper function
    def _conc_WHERE(cond_list, prefix="WHERE"):
        # If any conditions exist, concatenate by 'AND' strings.
        if len(cond_list) > 0:
            return prefix+" "+ " AND ".join(cond_list)
        return ""

    # State selection string
    # state_sel_str = """ SELECT {0} FROM {1} {2}""".format('state_id',
    #                                         NODE_STATE_TABLE_NAME,
    #                                         where_cond_str)
    # The state name map.
    sel_str = """SELECT {simulation_time} time, 
                        (SELECT {state_name} FROM {node_state_table} 
                                 WHERE {nt_node_id} == {et_node_id}) state, 
                        {weight} change 
                        FROM {event_table}
                        WHERE {et_node_id} IN (SELECT {nt_node_id} 
                                               FROM {node_state_table} 
                                               {ns_WHERE_str}) {et_time_cond}
                        """ # WHERE state IN ('I')
    sel_dict = {'simulation_time' : 'simulation_time',
                'event_table' : NODE_EVENT_TABLE_NAME,
                'state_name' : 'state_name',
                'nt_node_id' : 'state_id',
                'et_node_id' : NODE_EVENT_TABLE_SRC_STATE_COL,
                'node_state_table' : NODE_STATE_TABLE_NAME,
                'ns_WHERE_str' : _conc_WHERE(nstate_where_cond_list),
                'et_time_cond' : _conc_WHERE(nevent_where_cond_list,
                                             prefix="AND"),
                'weight' : -1}

    sel_src_str = sel_str.format(**sel_dict)
    sel_dict.update({'et_node_id' : NODE_EVENT_TABLE_DST_STATE_COL,
                     'weight' : 1})
    sel_dst_str = sel_str.format(**sel_dict)
    
    union_sel_str ="""{0} 
    UNION 
    {1}
    ORDER BY time;""".format(sel_src_str, sel_dst_str)

    print(union_sel_str)
    cur.execute(union_sel_str)
    return cur.fetchall()
    


