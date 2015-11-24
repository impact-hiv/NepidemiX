"""
sqlite3 IO
==========

Utility functions to extract data from NepidemiX sqlite3 output databases.
"""
__author__ =  "Lukas Ahrenberg (lukas@ahrenberg.se)"

__license__ = "Modified BSD License"


import sys

import numpy as np

import pickle

from nepidemix.utilities.networkxtra import entityCountSet

NODE_EVENT_TABLE_NAME = "node_event"
NODE_EVENT_TABLE_SRC_STATE_COL = "src_state"
NODE_EVENT_TABLE_DST_STATE_COL = "dst_state"
NODE_EVENT_TABLE_NODE_ID_COL = "node_id"
NODE_EVENT_TABLE_SIM_ID_COL = "simulation_id"
NODE_EVENT_TABLE_SIM_TIME_COL = "simulation_time"
NODE_EVENT_TABLE_MAJOR_IT_COL = "major_iteration"
NODE_EVENT_TABLE_MINOR_IT_COL = "minor_iteration"
NODE_STATE_TABLE_NAME = "node_state"
NODE_STATE_TABLE_ID_COL = "state_id"
SIMULATION_TABLE_NAME = "simulation"
SIMULATION_TABLE_SIM_ID_COL = NODE_EVENT_TABLE_SIM_ID_COL
SIMULATION_TABLE_NPX_V_COL = "nepidemix_version"
SIMULATION_TABLE_GRAPH_COL = "initial_graph"
SIMULATION_TABLE_CONF_COL =  "configuration"
SIMULATION_TABLE_TIME_COL = "time_stamp"
SIMULATION_TABLE_NUM_NODES_COL = "initial_node_count"
SIMULATION_TABLE_NUM_EDGES_COL = "initial_edge_count"

def get_flux(db_connection,
             state_A, state_B,
             time_min = None, time_max = None,
             simulation_set = None):
    """
    Get table with net flux between a set of states over a period of time.
    Positive means flux from state set A to state set B, 
    negative from state set B to A.

    Flux is defined as the fraction of network size state changes per unit time 
    at time t.

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

    simulation_set : iterable of integers
       This is the set of simulations (numbered from 1 and upwards) in the data
       base to include in the query. The average flux per time step will be 
       computed for this set. If None, all simulations are used.

    Returns
    -------
    table - The resulting time stamp and flux data.
    """
    # Open connection to db.
    cur = db_connection.cursor()
    
     # Helper function
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
        time_cond_list.append("time >= {0}".format(time_min))
    if time_max != None:
        time_cond_list.append("time < {0}".format(time_max))

    time_cond_str = _AND_conc_(time_cond_list)
    state_A_cond_str = _AND_conc_(state_A_cond_list, prefix='WHERE')
    state_B_cond_str = _AND_conc_(state_B_cond_list, prefix='WHERE')

    # SELECTion conditions for state A to state B
    # Source (A)
    AB_src_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_SRC_STATE_COL,
                                                NODE_STATE_TABLE_ID_COL,
                                                NODE_STATE_TABLE_NAME,
                                                state_A_cond_str)
    # Destination (B)
    AB_dst_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_DST_STATE_COL,
                                                NODE_STATE_TABLE_ID_COL,
                                                NODE_STATE_TABLE_NAME,
                                                state_B_cond_str)
    # SELECTion conditions for state B to state A
    # Source (B)
    BA_src_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_SRC_STATE_COL,
                                                NODE_STATE_TABLE_ID_COL,
                                                NODE_STATE_TABLE_NAME,
                                                state_B_cond_str)
    # Destination (A)
    BA_dst_str = _create_state_SELECT_condition(NODE_EVENT_TABLE_DST_STATE_COL,
                                                NODE_STATE_TABLE_ID_COL,
                                                NODE_STATE_TABLE_NAME,
                                                state_A_cond_str)
    
    # This selects the correct subset of simulations in case one is given.
    simulation_select_str = ""
    if simulation_set != None:
        simulation_select_str = "{0} IN ({1})"\
                                .format(NODE_EVENT_TABLE_SIM_ID_COL,
                                        ",".join([str(c) \
                                                  for c in simulation_set]))

    # Selects the number of nodes in the network.
    numnodes_sel_str = "(SELECT {0} FROM {1} WHERE {2} == {3})"\
                       .format(SIMULATION_TABLE_NUM_NODES_COL,
                               SIMULATION_TABLE_NAME,
                               SIMULATION_TABLE_SIM_ID_COL,
                               NODE_EVENT_TABLE_SIM_ID_COL)
        
    # The basic selection string.
    sel_str = """SELECT {simulation_time} time, 
                        {weight}/{numnodes} change 
                        FROM {event_table}
                        {ev_where_cond}""" 
    sel_base_dict = {'simulation_time' : NODE_EVENT_TABLE_SIM_TIME_COL,
                     'event_table' : NODE_EVENT_TABLE_NAME,
                     'numnodes' : numnodes_sel_str
    }
    AB_sel_dict = sel_base_dict.copy()
    AB_sel_dict.update({'weight' : 1.0,
                        'ev_where_cond': _AND_conc_([time_cond_str,
                                                     AB_src_str,
                                                     AB_dst_str,
                                                     simulation_select_str],
                                                    prefix='WHERE')})
    BA_sel_dict = sel_base_dict.copy()
    BA_sel_dict.update({'weight' : -1.0,
                        'ev_where_cond': _AND_conc_([time_cond_str,
                                                     BA_src_str,
                                                     BA_dst_str,
                                                     simulation_select_str],
                                                    prefix='WHERE')})
    


    sel_AB_str = sel_str.format(**AB_sel_dict)
    sel_BA_str = sel_str.format(**BA_sel_dict)

    union_sel_str ="""{0} 
    UNION ALL
    {1}
    ORDER BY time""".format(sel_AB_str, sel_BA_str)


    simulation_count_str = "SELECT COUNT({0}) FROM simulation "\
                           .format(SIMULATION_TABLE_SIM_ID_COL) +\
                           _AND_conc_([simulation_select_str], prefix = " WHERE ")
    
    # Compute the mean flux per time stamp as the sum of all flux at that time
    # (order by time) over the total number of simulations in selection.
    flux_sel_str = """ SELECT time, SUM(change)*1.0/({0}) flux
                       FROM ({1}) GROUP BY time;""".format(simulation_count_str,
                                                           union_sel_str)

    print(flux_sel_str)
    
    cur.execute(flux_sel_str)
    return cur.fetchall()


def mean_density(db_connection,
             state,
             time_min = None, time_max = None,
             simulation_set = None):
    """
    Mean density of a state in graph over time.

    For each time step returns the mean fraction of nodes in a given state set
    over all all simulations (or a subset of all simulations) in database.
    
    
    Parameters
    ----------
    db_connection : sqlite3.connection

    state : Python dict, Partial state
       This is a NepidemiX partial state set, defined as a dictionary where
       each key is a state attribute, and each value a python set (or other 
       iterable) with accepted values for this attribute. Non-listed 
       attributes may have any value.

    time_min : float
       Minimum simulation time (inclusive); if None the whole 
       simulation time frame is considered.

    time_max : float
       Minimum simulation time (exclusive); if None the whole 
       simulation time frame is considered.

    simulation_set : iterable of integers
       This is the set of simulations (numbered from 1 and upwards) in the data
       base to include in the query. The average flux per time step will be 
       computed for this set. If None, all simulations are used.

    Returns
    -------
    table - The resulting time stamp and density data.
    """

    cur = db_connection.cursor()
    # Retrieve the initial networks for all simulations in the simulation set
    # and count the number of nodes in the state set.

    # Do one simulation at a time in a loop. Slower, but networks can be
    # rather large, so to save mem...
    # If no subset of simulations are specified, it means all, and we need to
    # fetch a list of them.
    if simulation_set == None:
        cur.execute("SELECT {0} FROM {1};".format(SIMULATION_TABLE_SIM_ID_COL,
                                                  SIMULATION_TABLE_NAME))
        simulation_set = [s[0] for s in cur.fetchall()]

    avn = 0.0
    for sim in simulation_set:
        gn =0.0
        cur.execute("SELECT {0} FROM {1} WHERE {2} == {3};"\
                    .format(SIMULATION_TABLE_GRAPH_COL,
                            SIMULATION_TABLE_NAME,
                            SIMULATION_TABLE_SIM_ID_COL,
                            sim))
        
        graph = pickle.loads(cur.fetchall()[0][0])
        if len(state) < 1:
            gn += graph.number_of_nodes()
        else:
            for k,v in state.iteritems():
                for n in graph.nodes_iter(data=True):
                    if n[1][k] in [itm.strip("'").strip('"') for itm in v]:
                        gn += 1.0
        avn+=gn/graph.number_of_nodes()
        
    avn = avn/len(simulation_set)

    # Get the flux from all sets to state. The net flux will be negative if
    # nodes are leaving the state in question, and positive if going in to it.
    # Need to be taken all the way from time 0 as we only have an initial
    # count then.
    flx = np.array(get_flux(db_connection, {}, state,
                            time_min = 0, time_max = time_max,
                            simulation_set = simulation_set))

    # Add the original number of states to first flux item.
    flx[0,1] = flx[0,1] + avn

    # Compute cumulative sum of flux.
    flx[:,1] = flx[:,1].cumsum()

    # Pick out the rows where time is correct.
    flx = flx[flx[:,0] >= time_min]

    return flx
    

def _AND_conc_(cond_list, prefix=""):
    """"
    If any condition strings exist in cond_lost concatenate them
    by 'AND' strings, otherwise return empty string.
    Optional prefix string.
    """ 
    if len(cond_list) > 0:
        andstr = " AND ".join([str(c) for c in cond_list
                                       if len(str(c).strip()) > 0])
        rs = prefix+" "+ andstr
        if len(andstr) > 1:
            return rs
    return ""
