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



def get_flux(db_connection, state_A, state_B, time_min = None, time_max = None):
    """
    Get table with net flux between a set of states over a period of time.
    Positive means flux from state set A to state set B, 
    negative from state set B to A.

    Flux is defined as the number of state changes per unit time at time t.

    Parameters
    ----------
    db_connection : sqlite3.connection

    state_A : Python dict, Partial state
       This is a NepidemiX partial state set, defined as a dictionary where
       each key is a state attribute, and each value a python set (or other 
       iterable) with accepted values for this attribute. Non-listed 
       attributes may have any value. Positive flux will have its source in
       any state matching state_A.

    state_A : Python dict, Partial state
       This is a NepidemiX partial state set, defined as a dictionary where
       each key is a state attribute, and each value a python set (or other 
       iterable) with accepted values for this attribute. Non-listed 
       attributes may have any value. Negative flux will have its source in
       any state matching state_B.

    time_min : float
       Minimum simulation time for flux (inclusive); if None the whole 
       simulation time frame is considered.

    time_max : float
       Minimum simulation time for flux (exclusive); if None the whole 
       simulation time frame is considered.

    Returns
    -------
    table - The resulting time stamp and flux data.
    """
    # Open connection to db.
    cur = db_connection.cursor()
    
     # Helper functions
    def _AND_conc_(cond_list, prefix=""):
        """"
        If any condition strings exist in cond_lost concatenate them
        by 'AND' strings, otherwise return empty string.
        Optional prefix string.
        """ 
        if len(cond_list) > 0:
            rs = prefix+" "+ " AND ".join([c for c in cond_list
                                           if len(c.strip()) > 0])
            if len(rs) > 1:
                return rs
        return ""

    def _create_state_SELECT_condition(node_event_id_field,
                                       node_state_id_field,
                                       node_state_table_name,
                                       node_state_conditions):
        if None in [node_event_id_field,
                    node_state_id_field,
                    node_state_table_name,
                    node_state_conditions]:
            return ""
        return "{0} IN (SELECT {1} FROM {2} {3})".format(node_event_id_field,
                                                         node_state_id_field,
                                                         node_state_table_name,
                                                         node_state_conditions)
    
    # Node state table conditions added to this list.
    state_A_cond_list = []
    # The state options as a string;
    # Explanation: Strings on the form of <key> IN (<value1>, <value2>, ...)
    state_A_cond_list.extend(["{0} IN ({1})".format(k, ",".join(v))\
                              for k,v in state_A.iteritems()])
    state_B_cond_list = []
    # The state options as a string;
    # Explanation: Strings on the form of <key> IN (<value1>, <value2>, ...)
    state_B_cond_list.extend(["{0} IN ({1})".format(k, ",".join(v))\
                              for k,v in state_B.iteritems()])

    # Encoded time boundaries.
    time_cond_list = []
    if time_min != None:
        print(time_min)
        time_cond_list.append("time >= {0}".format(time_min))
    if time_max != None:
        time_cond_list.append("time < {0}".format(time_max))

    time_cond_str = _AND_conc_(time_cond_list)
    state_A_cond_str = _AND_conc_(state_A_cond_list, prefix='WHERE')
    state_B_cond_str = _AND_conc_(state_B_cond_list, prefix='WHERE')

    # SELECTion conditions for state A to state B
    # Source (A)
    AB_src_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_SRC_STATE_COL,
                                                'state_id',
                                                NODE_STATE_TABLE_NAME,
                                                state_A_cond_str)
    # Destination (B)
    AB_dst_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_DST_STATE_COL,
                                                'state_id',
                                                NODE_STATE_TABLE_NAME,
                                                state_B_cond_str)
    # SELECTion conditions for state B to state A
    # Source (B)
    BA_src_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_SRC_STATE_COL,
                                                'state_id',
                                                NODE_STATE_TABLE_NAME,
                                                state_B_cond_str)
    # Destination (A)
    BA_dst_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_DST_STATE_COL,
                                                'state_id',
                                                NODE_STATE_TABLE_NAME,
                                                state_A_cond_str)
    

    # The basic selection string.
    sel_str = """SELECT {simulation_time} time, 
                        {weight} change 
                        FROM {event_table}
                        {ev_where_cond}""" 
    sel_base_dict = {'simulation_time' : 'simulation_time',
                     'event_table' : NODE_EVENT_TABLE_NAME}
    AB_sel_dict = sel_base_dict.copy()
    AB_sel_dict.update({'weight' : 1,
                        'ev_where_cond': _AND_conc_([time_cond_str,
                                                     AB_src_str,
                                                     AB_dst_str], prefix='WHERE')})
    BA_sel_dict = sel_base_dict.copy()
    BA_sel_dict.update({'weight' : -1,
                        'ev_where_cond': _AND_conc_([time_cond_str,
                                                     BA_src_str,
                                                     BA_dst_str], prefix='WHERE')})
    


    sel_AB_str = sel_str.format(**AB_sel_dict)
    sel_BA_str = sel_str.format(**BA_sel_dict)

    union_sel_str ="""{0} 
    UNION ALL
    {1}
    ORDER BY time""".format(sel_AB_str, sel_BA_str)

    print(union_sel_str)
    flux_sel_str = """SELECT time, SUM(change) flux 
                       FROM ({0}) GROUP BY time;"""\
                           .format(union_sel_str)
    
    cur.execute(flux_sel_str)
    return cur.fetchall()

    


