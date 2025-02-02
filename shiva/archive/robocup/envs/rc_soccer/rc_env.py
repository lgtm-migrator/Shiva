import numpy as np
import time
import threading
import pandas as pd
import math
from .HFO.hfo import hfo
from .HFO import get_config_path, get_hfo_path, get_viewer_path
import os, subprocess, time, signal
from utils import misc as misc
from torch.autograd import Variable
import torch

possession_side = 'N'

class rc_env:
    """rc_env() extends the HFO environment to allow for centralized execution.
    Attributes:
        num_TA (int): Number of teammate agents. (0-11)
        num_OA (int): Number of opponent agents. (0-11)
        num_NPC (int): Number of opponent NPCs. (0-11)
        team_actions (list): List contains the current timesteps action for each
            agent. Takes value between 0 - num_states and is converted to HFO action by
            action_list.
        action_list (list): Contains the mapping from numer action value to HFO action.
        team_should_act (list of bools): Contains a boolean flag for each agent. Is
            activated to be True by Step function and becomes false when agent acts.
        team_should_act_flag (bool): Boolean flag is True if agents have
            unperformed actions, becomes False if all agents have acted.
        team_obs (list): List containing obs for each agent.
        team_obs_previous (list): List containing obs for each agent at previous timestep
        team_rewards (list): List containing reward for each agent
        start (bool): Once all agents have been launched, allows threads to listen for
            actions to take.
        world_states (list): Contains the status of the HFO world.
        team_envs (list of HFOEnvironment objects): Contains an HFOEnvironment object
            for each agent on team.
        opp_xxx attributes: Extend the same functionality for user controlled team
            to opposing team.
    Todo:
        * Functionality for synchronizing team actions with opponent team actions
        * Add the ability for team agents to function with npcs taking the place of opponents
        """
    # class constructor
    # def __init__(self, num_TNPC=0,num_TA = 1,num_OA = 0,num_ONPC = 1,base = 'base_left',
    #              goalie = False, num_trials = 10000,fpt = 100,feat_lvl = 'high',
    #              act_lvl = 'low',untouched_time = 100, sync_mode = True, port = 6000,
    #              offense_on_ball=0, fullstate = False, seed = 123,
    #              ball_x_min = -0.8, ball_x_max = 0.8, ball_y_min = -0.8, ball_y_max = 0.8,
    #              verbose = False, rcss_log_game=False, hfo_log_game=False, log_dir="logs",team_rew_anneal_ep=1000,
    #              agents_x_min=-0.8, agents_x_max=0.8, agents_y_min=-0.8, agents_y_max=0.8,
    #              change_every_x=5, change_agents_x=0.1, change_agents_y=0.1, change_balls_x=0.1,
    #              change_balls_y=0.1, control_rand_init=False,record=False,record_server=False,
    #              defense_team_bin='helios15', offense_team_bin='helios16', run_server=False, deterministic=True):

    def __init__(self, config, port):
        self.config = config

        self.pass_reward = 0.0
        self.agent_possession_team = ['N'] * config.num_left
        self.team_passer = [0]*config.num_left
        self.opp_passer = [0]*config.num_left
        self.team_lost_possession = [0]*config.num_left
        self.opp_lost_possession = [0]*config.num_left
        self.agent_possession_opp = ['N'] * config.num_right
        self.team_possession_counter = [0] * config.num_left
        self.opp_possession_counter = [0] * config.num_right
        self.team_kickable = [0] * config.num_right
        self.opp_kickable = [0] * config.num_right
        self.offense_on_ball = config.offense_ball

        self.untouched = config.untouched

        self.goalie = config.goalie
        self.team_rew_anneal_ep = config.reward_anneal
        self.port = port
        self.hfo_path = get_hfo_path()
        self.seed = np.random.randint(1000)

        self.viewer = None

        # params for low level actions
        num_action_params = 5 # 2 for dash and kick 1 for turn and tackle
        self.team_action_params = np.asarray([[0.0]*num_action_params for i in range(config.num_left)])
        self.opp_action_params = np.asarray([[0.0]*num_action_params for i in range(config.num_right)])
        if config.al == 'low':
            #                   pow,deg   deg       deg         pow,deg    
            #self.action_list = [hfo.DASH, hfo.TURN, hfo.TACKLE, hfo.KICK]
            self.action_list = [hfo.DASH, hfo.TURN, hfo.KICK]

            self.kick_actions = [hfo.KICK] # actions that require the ball to be kickable
    
        elif config.al == 'high':
            self.action_list = [hfo.DRIBBLE, hfo.SHOOT, hfo.REORIENT, hfo.GO_TO_BALL, hfo.MOVE]
            self.kick_actions = [hfo.DRIBBLE, hfo.SHOOT, hfo.PASS] # actions that require the ball to be kickable
        
        self.num_TA = config.num_left
        self.num_OA = config.num_right
        self.num_ONPC = config.num_r_bot
        self.num_TNPC = config.num_l_bot

        self.base = 'base_left'
        self.fpt = config.ep_length
        self.been_kicked_team = False
        self.been_kicked_opp = False
        self.act_lvl = config.al
        self.feat_lvl = config.fl
        self.team_possession = False
        self.opp_possession = False
        if config.fl == 'low':
            #For new obs reorganization without vailds, changed hfo obs from 59 to 56
            self.team_num_features = 56 + 13*(config.num_left-1) + 12*config.num_right + 4 + 1 + 2 + 1  + 8
            self.opp_num_features = 56 + 13*(config.num_right-1) + 12*config.num_left + 4 + 1 + 2 + 1 + 8
        elif config.fl == 'high':
            self.team_num_features = (6*config.num_left) + (3*config.num_right) + (3*num_ONPC) + 6
            self.opp_num_features = (6*config.num_right) + (3*config.num_left) + (3*num_ONPC) + 6
        elif config.fl == 'simple':
            # 16 - land_feats + 12 - basic feats + 6 per (team/opp)
            self.team_num_features = 28 + (6 * ((config.num_left-1) + config.num_right)) + 8
            self.opp_num_features = 28 + (6 * (config.num_left + (config.num_right-1))) + 8

        self.acs_dim = config.total_ac_dim
        # Feature indexes by name
        self.stamina = 26
        self.ball_x = 16
        self.ball_y = 17
        self.ball_x_vel = 18
        self.ball_y_vel = 19
        self.x = 20
        self.y = 21
        self.x_vel = 22
        self.y_vel = 23
        self.opp_goal_top_x = 12
        self.opp_goal_top_y = 13
        self.opp_goal_bot_x = 14
        self.opp_goal_bot_y = 15

        # self._start_hfo_server()
        # self.team_envs = [hfo.HFOEnvironment() for i in range(config.num_left)]
        # self.opp_team_envs = [hfo.HFOEnvironment() for i in range(config.num_right)]
        self.team_envs = None
        self.opp_team_envs = None

        # flag that says when the episode is done
        self.d = 0

        # flag to wait for all the agents to load
        self.start = False

        self.sync_after_queue = threading.Barrier(config.num_left+config.num_right+1)
        self.sync_before_step = threading.Barrier(config.num_left+config.num_right+1)
        self.sync_at_status = threading.Barrier(config.num_left+config.num_right)
        self.sync_at_reward = threading.Barrier(config.num_left+config.num_right)

        # Initialization of mutable lists to be passsed to threads
        # action each team mate is supposed to take when its time to act
        self.team_actions = np.array([2]*config.num_left)
        # observation space for all team mate agents
        self.team_obs = np.empty([config.num_left,self.team_num_features],dtype=float)
        # previous state for all team agents
        self.team_obs_previous = np.empty([config.num_left,self.team_num_features],dtype=float)
        self.team_actions_OH = np.empty([config.num_left,8],dtype=float)
        self.opp_actions_OH = np.empty([config.num_left,8],dtype=float)

        # reward for each agent
        self.team_rewards = np.zeros(config.num_left)

        self.opp_actions = np.array([2]*config.num_right)
        # observation space for all team mate agents
        self.opp_team_obs = np.empty([config.num_right,self.opp_num_features],dtype=float)
        # previous state for all team agents
        self.opp_team_obs_previous = np.empty([config.num_right,self.opp_num_features],dtype=float)
        # reward for each agent
        self.opp_rewards = np.zeros(config.num_right)

        # keeps track of world state
        self.world_status = 0
        
        self.team_base = self.base
        self.opp_base = ''

        # Create thread for each opponent (set one to goalie)
        if self.base == 'base_left':
            self.opp_base = 'base_right'
        elif self.base == 'base_right':
            self.opp_base = 'base_left'
        
    def launch(self):
        self._start_hfo_server()
        self.team_envs = [hfo.HFOEnvironment() for i in range(self.config.num_left)]
        self.opp_team_envs = [hfo.HFOEnvironment() for i in range(self.config.num_right)]
        
        # Create thread for each teammate
        for i in range(self.num_TA):
            if i == 0:
                print("Connecting player %i" % i , "on team %s to the server" % self.base)
                # thread.start_new_thread(self.connect,(self.port,self.feat_lvl, self.base,
                #                                 self.goalie,i,self.fpt,self.act_lvl,))
                t = threading.Thread(target=self.connect, args=(self.port,self.feat_lvl, self.base,
                                                self.goalie,i,self.fpt,self.act_lvl,))
                print("herereerr")
                t.start()
                print("herereerr")
            else:
                print("Connecting player %i" % i , "on team %s to the server" % self.base)
                # thread.start_new_thread(self.connect,(self.port,self.feat_lvl, self.base,
                #                                 False,i,self.fpt,self.act_lvl,))
                t = threading.Thread(target=self.connect, args=(self.port,self.feat_lvl, self.base,
                                                False,i,self.fpt,self.act_lvl,))
                t.start()
            print('This is printed next')
            time.sleep(1.5)
        
        for i in range(self.num_OA):
            if i == 0:
                print("Connecting player %i" % i , "on Opponent %s to the server" % self.opp_base)
                # thread.start_new_thread(self.connect,(self.port,self.feat_lvl, self.opp_base,
                #                                 self.goalie,i,self.fpt,self.act_lvl,))
                t = threading.Thread(target=self.connect, args=(self.port,self.feat_lvl, self.opp_base,
                                                self.goalie,i,self.fpt,self.act_lvl,))
                t.start()
            else:
                print("Connecting player %i" % i , "on Opponent %s to the server" % self.opp_base)
                # thread.start_new_thread(self.connect,(self.port,self.feat_lvl, self.opp_base,
                #                                 False,i,self.fpt,self.act_lvl,))
                t = threading.Thread(target=self.connect, args=(self.port,self.feat_lvl, self.opp_base,
                                                False,i,self.fpt,self.act_lvl,))
                t.start()

            time.sleep(1.5)
        print("All players connected to server")
        self.start = True

        

    def Observation(self,agent_id,side):
        """ Requests and returns observation from an agent from either team.
        Args:
            agent_id (int): Agent to receive observation from. (0-11)
            side (str): Which team agent belongs to. ('team', 'opp')
        Returns:
            Observation from requested agent.
        """

        if side == 'team':
            return self.team_obs[agent_id]
        elif side == 'opp':
            return self.opp_team_obs[agent_id]

    def Reward(self,agent_id,side):
        """ Requests and returns reward from an agent from either team.
        Args:
            agent_id (int): Agent to receive observation from. (0-11)
            side (str): Which team agent belongs to. ('team', 'opp')
        Returns:
            Reward from requested agent.
        """
        if side == 'team':
            return self.team_rewards[agent_id]
        elif side == 'opp':
            return self.opp_rewards[agent_id]


    def Step(self, team_actions, opp_actions, team_params=[], opp_params=[],team_actions_OH = [],opp_actions_OH = []):
        """ Performs each agents' action from actions and returns tuple (obs,rewards,world_status)
        Args:
            actions (list of ints); List of integers corresponding to the action each agent will take
            side (str): Which team agent belongs to. ('team', 'opp')
        Returns:
            Status of HFO World
        Todo:
            * Add functionality for opp team
        """
        # Queue actions for team
        for i in range(self.num_TA):
            self.team_actions_OH[i] = misc.zero_params(team_actions_OH[i].reshape(-1))
            self.opp_actions_OH[i] = misc.zero_params(opp_actions_OH[i].reshape(-1))
        [self.Queue_action(i,self.team_base,team_actions[i],team_params) for i in range(len(team_actions))]
        # Queue actions for opposing team
        [self.Queue_action(j,self.opp_base,opp_actions[j],opp_params) for j in range(len(opp_actions))]

        self.sync_after_queue.wait()

        self.sync_before_step.wait()

        self.team_rewards = [rew + self.pass_reward if passer else rew for rew,passer in zip(self.team_rewards,self.team_passer)]
        self.opp_rewwards =[rew + self.pass_reward if passer else rew for rew,passer in zip(self.opp_rewards,self.opp_passer)]
        

        self.team_rewards = np.add( self.team_rewards, self.team_lost_possession)
        self.opp_rewards = np.add(self.opp_rewards, self.opp_lost_possession)


        self.team_passer = [0]*self.num_TA
        self.opp_passer = [0]*self.num_TA
        self.team_lost_possession = [0]*self.num_TA
        self.opp_lost_possession = [0]*self.num_TA
        return np.asarray(self.team_obs),self.team_rewards,np.asarray(self.opp_team_obs),self.opp_rewards, \
                self.d, self.world_status



    def Queue_action(self,agent_id,base,action,params=[]):
        """ Queues an action on agent, and if all agents have received action instructions performs the actions.
        Args:
            agent_id (int): Agent to receive observation from. (0-11)
            base (str): Which side an agent belongs to. ('base_left', 'base_right')
        """

        if self.team_base == base:
            self.team_actions[agent_id] = action
            if self.act_lvl == 'low':
                for p in range(params.shape[1]):
                    self.team_action_params[agent_id][p] = params[agent_id][p]
        else:
            self.opp_actions[agent_id] = action
            if self.act_lvl == 'low':
                for p in range(params.shape[1]):
                    self.opp_action_params[agent_id][p] = params[agent_id][p]


#################################################
######################  Utils for Reward ########
#################################################

    def get_kickable_status(self,agentID,env):
        ball_kickable = False
        ball_kickable = env.isKickable()
        #print("no implementation")
        return ball_kickable
    
    def get_agent_possession_status(self,agentID,base):
        if self.team_base == base:
            if self.agent_possession_team[agentID] == 'L':
                self.team_possession_counter[agentID] += 1
            
            return self.team_possession_counter[agentID]
        else:
            if self.agent_possession_opp[agentID] == 'R':
                self.opp_possession_counter[agentID] += 1
        #    print("no implementation")
            return self.opp_possession_counter[agentID]  



    def closest_player_to_ball(self, team_obs, num_agents):
        '''
        teams receive reward based on the distance of their closest agent to the ball
        '''
        closest_player_index = 0
        ball_distance = self.distance_to_ball(team_obs[0])
        for i in range(1, num_agents):
            temp_distance = self.distance_to_ball(team_obs[i])
            if temp_distance < ball_distance:
                closest_player_index = i
                ball_distance = temp_distance
        return ball_distance, closest_player_index
    
    def agent_possession_reward(self,base,agentID):
        '''
        agent receives reward for possessing ball
        '''
        rew_amount = 0.001
        if self.team_base == base:
            if self.agent_possession_team[agentID] == 'L':
                return rew_amount
        else:
            if self.agent_possession_opp[agentID] == 'R':
                return rew_amount
        return 0.0
                
    def unnormalize_unif(self,unif):
        print("no implementation")
        return int(np.round(unif * 100,decimals=0))
            
    def team_possession_reward(self,base):

        '''
        teams receive reward based on possession defined by which side had the ball kickable last
        '''
        rew_amount = 0.001
        global possession_side
        if self.team_base == base:
            if  possession_side == 'L':
                    return rew_amount
            if  possession_side == 'R':
                    return -rew_amount
        else: 
            if  possession_side == 'R':
                    return rew_amount
            if  possession_side == 'L':
                    return -rew_amount
        #print("no implementation")
        return 0.0
        
        
    def ball_distance_to_goal(self,obs):
        goal_center_x = 1.0
        goal_center_y = 0.0
        relative_x = obs[self.ball_x] - goal_center_x
        relative_y = obs[self.ball_y] - goal_center_y
        ball_distance_to_goal = math.sqrt(relative_x**2 + relative_y**2)
        return ball_distance_to_goal
    
 
    def distance_to_ball(self, obs):
        relative_x = obs[self.x]-obs[self.ball_x]
        relative_y = obs[self.y]-obs[self.ball_y]
        ball_distance = math.sqrt(relative_x**2+relative_y**2)
        
        return ball_distance
    
    # takes param index (0-4)
    def get_valid_scaled_param(self,agentID,param,base):
        if self.team_base == base:
            self.action_params = self.team_action_params
        else:
            self.action_params = self.opp_action_params

        if param == 0: # dash power
            #return ((self.action_params[agentID][0].clip(-1,1) + 1)/2)*100
            return self.action_params[agentID][0].clip(-1,1)*100
        elif param == 1: # dash deg
            return self.action_params[agentID][1].clip(-1,1)*180
        elif param == 2: # turn deg
            return self.action_params[agentID][2].clip(-1,1)*180
        # tackle deg
        elif param == 3: # kick power
            return ((self.action_params[agentID][3].clip(-1,1) + 1)/2)*100
        elif param == 4: # kick deg
            return self.action_params[agentID][4].clip(-1,1)*180

        # with tackle


    def get_excess_param_distance(self,agentID,base):
        if self.team_base == base:
            self.action_params = self.team_action_params
        else:
            self.action_params = self.opp_action_params

        distance = 0
        distance += (self.action_params[agentID][0].clip(-1,1) - self.action_params[agentID][0])**2
        distance += (self.action_params[agentID][1].clip(-1,1) - self.action_params[agentID][1])**2
        distance += (self.action_params[agentID][2].clip(-1,1) - self.action_params[agentID][2])**2
        distance += (self.action_params[agentID][3].clip(-1,1) - self.action_params[agentID][3])**2
        distance += (self.action_params[agentID][4].clip(-1,1) - self.action_params[agentID][4])**2
        return distance

    
    def getPretrainRew(self,s,d,base):
        

        reward=0.0
        team_reward = 0.0
        goal_points = 30.0
        #---------------------------
        global possession_side
        if d:
            if self.team_base == base:
            # ------- If done with episode, don't calculate other rewards (reset of positioning messes with deltas) ----
                if s==1:
                    reward+= goal_points
                elif s==2:
                    reward+=-goal_points
                elif s==3:
                    reward+=-0.5
                elif s==6:
                    reward+= +goal_points/5.0
                elif s==7:
                    reward+= -goal_points/4.0

                return reward
            else:
                if s==1:
                    reward+=-goal_points
                elif s==2:
                    reward+=goal_points
                elif s==3:
                    reward+=-0.5
                elif s==6:
                    reward+= -goal_points/4.0
                elif s==7:
                    reward+= goal_points/5.0

        return reward
       
    def distance(self,x1,x2,y1,y2):
        return math.sqrt((x1-x2)**2 + (y1-y2)**2)

    def distances(self,agentID,side):
        if side == 'left':
            team_obs = self.team_obs
            opp_obs =  self.opp_team_obs
        elif side =='right':
            team_obs = self.opp_team_obs
            opp_obs = self.team_obs
        else:
            print("Error: Please return a side: ('left', 'right') for side parameter")

        distances_team = []
        distances_opp = []
        for i in range(len(team_obs)):
            distances_team.append(self.distance(team_obs[agentID][self.x],team_obs[i][self.x], team_obs[agentID][self.y],team_obs[i][self.y]))
            distances_opp.append(self.distance(team_obs[agentID][self.x], -opp_obs[i][self.x], team_obs[agentID][self.y], -opp_obs[i][self.y]))
        return np.argsort(distances_team), np.argsort(distances_opp)


    def unnormalize(self,val):
        return (val +1.0)/2.0
    
    # Engineered Reward Function
    #   To-do: Add the ability of team agents to know if opponent npcs hold ball posession. For now, having npc opponent disables first kick award
    def getReward(self,s,agentID,base,ep_num):
        reward=0.0
        team_reward = 0.0
        goal_points = 20.0
        #---------------------------
        global possession_side
        if self.d:
            if self.team_base == base:
            # ------- If done with episode, don't calculate other rewards (reset of positioning messes with deltas) ----
                if s=='Goal_By_Left' and self.agent_possession_team[agentID] == 'L':
                    reward+= goal_points
                elif s=='Goal_By_Left':
                    reward+= goal_points # teammates get 10% of points
                elif s=='Goal_By_Right':
                    reward+=-goal_points
                elif s=='OutOfBounds' and self.agent_possession_team[agentID] == 'L':
                    reward+=-0.5
                elif s=='CapturedByLeftGoalie':
                    reward+=goal_points/5.0
                elif s=='CapturedByRightGoalie':
                    reward+= 0 #-goal_points/4.0

                possession_side = 'N' # at the end of each episode we set this to none
                self.agent_possession_team = ['N'] * self.num_TA
                return reward
            else:
                if s=='Goal_By_Right' and self.agent_possession_opp[agentID] == 'R':
                    reward+=goal_points
                elif s=='Goal_By_Right':
                    reward+=goal_points
                elif s=='Goal_By_Left':
                    reward+=-goal_points
                elif s=='OutOfBounds' and self.agent_possession_opp[agentID] == 'R':
                    reward+=-0.5
                elif s=='CapturedByRightGoalie':
                    reward+=goal_points/5.0
                elif s=='CapturedByLeftGoalie':
                    reward+= 0 #-goal_points/4.0

                possession_side = 'N'
                self.agent_possession_opp = ['N'] * self.num_OA
                return reward
        

        
        if self.team_base == base:
            team_actions = self.team_actions
            team_obs = self.team_obs
            team_obs_previous = self.team_obs_previous
            opp_obs = self.opp_team_obs
            opp_obs_previous = self.opp_team_obs_previous
            num_ag = self.num_TA
            env = self.team_envs[agentID]
            kickable = self.team_kickable[agentID]
            self.team_kickable[agentID] = self.get_kickable_status(agentID,env)
        else:
            team_actions = self.opp_actions
            team_obs = self.opp_team_obs
            team_obs_previous = self.opp_team_obs_previous
            opp_obs = self.team_obs
            opp_obs_previous = self.team_obs_previous
            num_ag = self.num_OA
            env = self.opp_team_envs[agentID]
            kickable = self.opp_kickable[agentID]
            self.opp_kickable[agentID] = self.get_kickable_status(agentID,env)# update kickable status (it refers to previous timestep, e.g., it WAS kickable )

        if team_obs[agentID][self.stamina] < 0.0 : # LOW STAMINA
            reward -= 0.003
            team_reward -= 0.003
            # print ('low stamina')
        


        ############ Kicked Ball #################
        
        if self.action_list[team_actions[agentID]] in self.kick_actions and kickable:            
            if self.num_OA > 0:
                if (np.array(self.agent_possession_team) == 'N').all() and (np.array(self.agent_possession_opp) == 'N').all():
                     #print("First Kick")
                    reward += 1.5
                    team_reward +=1.5
                # set initial ball position after kick
                    if self.team_base == base:
                        self.BL_ball_pos_x = team_obs[agentID][self.ball_x]
                        self.BL_ball_pos_y = team_obs[agentID][self.ball_y]
                    else:
                        self.BR_ball_pos_x = team_obs[agentID][self.ball_x]
                        self.BR_ball_pos_y = team_obs[agentID][self.ball_y]
                        

        #     # track ball delta in between kicks
            if self.team_base == base:
                self.BL_ball_pos_x = team_obs[agentID][self.ball_x]
                self.BL_ball_pos_y = team_obs[agentID][self.ball_y]
            else:
                self.BR_ball_pos_x = team_obs[agentID][self.ball_x]
                self.BR_ball_pos_y = team_obs[agentID][self.ball_y]

            new_x = team_obs[agentID][self.ball_x]
            new_y = team_obs[agentID][self.ball_y]
            
            if self.team_base == base:
                ball_delta = math.sqrt((self.BL_ball_pos_x-new_x)**2+ (self.BL_ball_pos_y-new_y)**2)
                self.BL_ball_pos_x = new_x
                self.BL_ball_pos_y = new_y
            else:
                ball_delta = math.sqrt((self.BR_ball_pos_x-new_x)**2+ (self.BR_ball_pos_y-new_y)**2)
                self.BR_ball_pos_x = new_x
                self.BR_ball_pos_y = new_y
            
            self.pass_reward = ball_delta * 5.0

        #     ######## Pass Receiver Reward #########
            if self.team_base == base:
                if (np.array(self.agent_possession_team) == 'L').any():
                    prev_poss = (np.array(self.agent_possession_team) == 'L').argmax()
                    if not self.agent_possession_team[agentID] == 'L':
                        self.team_passer[prev_poss] += 1 # sets passer flag to whoever passed
                        # Passer reward is added in step function after all agents have been checked
                       
                        reward += self.pass_reward
                        team_reward += self.pass_reward
                        #print("received a pass worth:",self.pass_reward)
        #               #print('team pass reward received ')
        #         #Remove this check when npc ball posession can be measured
                if self.num_OA > 0:
                    if (np.array(self.agent_possession_opp) == 'R').any():
                        enemy_possessor = (np.array(self.agent_possession_opp) == 'R').argmax()
                        self.opp_lost_possession[enemy_possessor] -= 1.0
                        self.team_lost_possession[agentID] += 1.0
                        # print('BR lost possession')
                        self.pass_reward = 0

        #         ###### Change Possession Reward #######
                self.agent_possession_team = ['N'] * self.num_TA
                self.agent_possession_opp = ['N'] * self.num_OA
                self.agent_possession_team[agentID] = 'L'
                if possession_side != 'L':
                    possession_side = 'L'    
                    #reward+=1
                    #team_reward+=1
            else:
                # self.opp_possession_counter[agentID] += 1
                if (np.array(self.agent_possession_opp) == 'R').any():
                    prev_poss = (np.array(self.agent_possession_opp) == 'R').argmax()
                    if not self.agent_possession_opp[agentID] == 'R':
                        self.opp_passer[prev_poss] += 1 # sets passer flag to whoever passed
                        reward += self.pass_reward
                        team_reward += self.pass_reward
        #                 # print('opp pass reward received ')

                if (np.array(self.agent_possession_team) == 'L').any():
                    enemy_possessor = (np.array(self.agent_possession_team) == 'L').argmax()
                    self.team_lost_possession[enemy_possessor] -= 1.0
                    self.opp_lost_possession[agentID] += 1.0
                    self.pass_reward = 0
      #             # print('BL lost possession ')

                self.agent_possession_team = ['N'] * self.num_TA
                self.agent_possession_opp = ['N'] * self.num_OA
                self.agent_possession_opp[agentID] = 'R'
                if possession_side != 'R':
                    possession_side = 'R'
                    #reward+=1
                    #team_reward+=1

        ####################### reduce distance to ball - using delta  ##################
        # all agents rewarded for closer to ball
        # dist_cur = self.distance_to_ball(team_obs[agentID])
        # dist_prev = self.distance_to_ball(team_obs_previous[agentID])
        # d = (0.5)*(dist_prev - dist_cur) # if cur > prev --> +   
        # if delta > 0:
        #     reward  += delta
        #     team_reward += delta
            
        ####################### Rewards the closest player to ball for advancing toward ball ############
        distance_cur,_ = self.closest_player_to_ball(team_obs, num_ag)
        distance_prev, closest_agent = self.closest_player_to_ball(team_obs_previous, num_ag)
        if agentID == closest_agent:
            delta = (distance_prev - distance_cur)*1.0
            #if delta > 0:    
            if True:
                team_reward += delta
                reward+= delta
            
        ##################################################################################
            
        ####################### reduce ball distance to goal ##################
        # base left kicks
        r = self.ball_distance_to_goal(team_obs[agentID]) 
        r_prev = self.ball_distance_to_goal(team_obs_previous[agentID]) 
        if ((self.team_base == base) and possession_side =='L'):
            team_possessor = (np.array(self.agent_possession_team) == 'L').argmax()
            if agentID == team_possessor:
                delta = (2*self.num_TA)*(r_prev - r)
                if True:
                #if delta > 0:
                    reward += delta
                    team_reward += delta

        # base right kicks
        elif  ((self.team_base != base) and possession_side == 'R'):
            team_possessor = (np.array(self.agent_possession_opp) == 'R').argmax()
            if agentID == team_possessor:
                delta = (2*self.num_TA)*(r_prev - r)
                if True:
                #if delta > 0:
                    reward += delta
                    team_reward += delta
                    
        # non-possessor reward for ball delta toward goal
        else:
            delta = (0*self.num_TA)*(r_prev - r)
            if True:
            #if delta > 0:
                reward += delta
                team_reward += delta       

        # ################## Offensive Behavior #######################
        # # [Offense behavior]  agents will be rewarded based on maximizing their open angle to opponents goal ( only for non possessors )
        # if ((self.team_base == base) and possession_side =='L') or ((self.team_base != base) and possession_side == 'R'): # someone on team has ball
        #     b,_,_ =self.ball_distance_to_goal(team_obs[agentID]) #r is maxed at 2sqrt(2)--> 2.8
        #     if b < 1.5 : # Ball is in scoring range
        #         if (self.apprx_to_goal(team_obs[agentID]) > 0.0) and (self.apprx_to_goal(team_obs[agentID]) < .85):
        #             a = self.unnormalize(team_obs[agentID][self.open_goal])
        #             a_prev = self.unnormalize(team_obs_previous[agentID][self.open_goal])
        #             if (self.team_base != base):    
        #                 team_possessor = (np.array(self.agent_possession_opp) == 'R').argmax()
        #             else:
        #                 team_possessor = (np.array(self.agent_possession_team) == 'L').argmax()
        #             if agentID != team_possessor:
        #                 reward += (a-a_prev)*2.0
        #                 team_reward += (a-a_prev)*2.0
        #             #print("offense behavior: goal angle open ",(a-a_prev)*3.0)


        # # [Offense behavior]  agents will be rewarded based on maximizing their open angle to the ball (to receive pass)
        # if self.num_TA > 1:
        #     if ((self.team_base == base) and possession_side =='L') or ((self.team_base != base) and possession_side == 'R'): # someone on team has ball
        #         if (self.team_base != base):
                    
        #             team_possessor = (np.array(self.agent_possession_opp) == 'R').argmax()
        #             #print("possessor is base right agent",team_possessor)

        #         else:
        #             team_possessor = (np.array(self.agent_possession_team) == 'L').argmax()
        #             #print("possessor is base left agent",team_possessor)

        #         unif_nums = np.array([self.unnormalize_unif(val) for val in team_obs[team_possessor][self.team_unif_beg:self.team_unif_end]])
        #         unif_nums_prev = np.array([self.unnormalize_unif(val) for val in team_obs_previous[team_possessor][self.team_unif_beg:self.team_unif_end]])
        #         if agentID != team_possessor:
        #             if not (-100 in unif_nums) and not (-100 in unif_nums_prev):
        #                 angle_delta = self.unnormalize(team_obs[team_possessor][self.team_pass_angle_beg + np.argwhere(unif_nums == (agentID+1))[0][0]]) - self.unnormalize(team_obs_previous[team_possessor][self.team_pass_angle_beg+np.argwhere(unif_nums_prev == (agentID+1))[0][0]])
        #                 reward += angle_delta
        #                 team_reward += angle_delta
        #                 #print("offense behavior: pass angle open ",angle_delta*3.0)

                    

        # ################## Defensive behavior ######################

        # # [Defensive behavior]  agents will be rewarded based on minimizing the opponents open angle to our goal
        # if ((self.team_base != base) and possession_side == 'L'): # someone on team has ball
        #     enemy_possessor = (np.array(self.agent_possession_team) == 'L').argmax()
        #     #print("possessor is base left agent",enemy_possessor)
        #     agent_inds = np.where([self.apprx_to_goal(opp_obs[i]) > -0.75 for i in range(self.num_TA)])[0] # find who is in range

        #     b,_,_ =self.ball_distance_to_goal(opp_obs[agentID]) #r is maxed at 2sqrt(2)--> 2.8

        #     if b < 1.5 : # Ball is in scoring range
        #         if np.array([self.apprx_to_goal(opp_obs[i]) > -0.75 for i in range(self.num_TA)]).any(): # if anyone is in range on enemy team
        #             sum_angle_delta = np.sum([(self.unnormalize(opp_obs_previous[i][self.open_goal]) - self.unnormalize(opp_obs[i][self.open_goal])) for i in agent_inds]) # penalize based on the open angles of the people in range
        #             reward += sum_angle_delta*2.0
        #             team_reward += sum_angle_delta*2.0
        #             angle_delta_possessor = self.unnormalize(opp_obs_previous[enemy_possessor][self.open_goal]) - self.unnormalize(opp_obs[enemy_possessor][self.open_goal])# penalize based on the open angles of the possessor
        #             reward += angle_delta_possessor*2.0
        #             team_reward += angle_delta_possessor*2.0
        #             #print("defensive behavior: block open angle to goal",agent_inds)
        #             #print("areward for blocking goal: ",angle_delta_possessor*3.0)

        # elif ((self.team_base == base) and possession_side =='R'): 
        #     enemy_possessor = (np.array(self.agent_possession_opp) == 'R').argmax()
        #     #print("possessor is base right agent",enemy_possessor)
        #     agent_inds = np.where([self.apprx_to_goal(opp_obs[i]) > -0.75 for i in range(self.num_TA)])[0] # find who is in range

        #     b,_,_ =self.ball_distance_to_goal(opp_obs[agentID]) #r is maxed at 2sqrt(2)--> 2.8
        #     if b < 1.5 : # Ball is in scoring range
        #         if np.array([self.apprx_to_goal(opp_obs[i]) > -0.75 for i in range(self.num_TA)]).any(): # if anyone is in range on enemy team
        #             sum_angle_delta = np.sum([(self.unnormalize(opp_obs_previous[i][self.open_goal]) - self.unnormalize(opp_obs[i][self.open_goal])) for i in agent_inds]) # penalize based on the open angles of the people in range
        #             reward += sum_angle_delta*2.0
        #             team_reward += sum_angle_delta*2.0
        #             angle_delta_possessor = self.unnormalize(opp_obs_previous[enemy_possessor][self.open_goal]) - self.unnormalize(opp_obs[enemy_possessor][self.open_goal])# penalize based on the open angles of the possessor
        #             reward += angle_delta_possessor*2.0
        #             team_reward += angle_delta_possessor*2.0
        #             #print("defensive behavior: block open angle to goal",agent_inds)
        #             #print("areward for blocking goal: ",angle_delta_possessor*3.0)




        # # [Defensive behavior]  agents will be rewarded based on minimizing the ball open angle to other opponents (to block passes )
        # if self.num_TA > 1:
                
        #     if ((self.team_base != base) and possession_side == 'L'): # someone on team has ball
        #         enemy_possessor = (np.array(self.agent_possession_team) == 'L').argmax()
        #         sum_angle_delta = np.sum([(self.unnormalize(opp_obs_previous[enemy_possessor][self.team_pass_angle_beg+i]) - self.unnormalize(opp_obs[enemy_possessor][self.team_pass_angle_beg+i])) for i in range(self.num_TA-1)]) # penalize based on the open angles of the people in range
        #         reward += sum_angle_delta*0.3/float(self.num_TA)
        #         team_reward += sum_angle_delta*0.3/float(self.num_TA)
        #         #print("defensive behavior: block open passes",enemy_possessor,"has ball")
        #         #print("reward for blocking",sum_angle_delta*3.0/self.num_TA)

        #     elif ((self.team_base == base) and possession_side =='R'):
        #         enemy_possessor = (np.array(self.agent_possession_opp) == 'R').argmax()
        #         sum_angle_delta = np.sum([(self.unnormalize(opp_obs_previous[enemy_possessor][self.team_pass_angle_beg+i]) - self.unnormalize(opp_obs[enemy_possessor][self.team_pass_angle_beg+i])) for i in range(self.num_TA-1)]) # penalize based on the open angles of the people in range
        #         reward += sum_angle_delta*0.3/float(self.num_TA)
        #         team_reward += sum_angle_delta*0.3/float(self.num_TA)
        #         #print("defensive behavior: block open passes",enemy_possessor,"has ball")
        #         #print("reward for blocking",sum_angle_delta*6.0/float(self.num_TA))

        ##################################################################################
        rew_percent = 1.0*max(0,(self.team_rew_anneal_ep - ep_num))/self.team_rew_anneal_ep
        return ((1.0 - rew_percent)*team_reward) + (reward * rew_percent)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def connect(self,port,feat_lvl, base, goalie, agent_ID,fpt,act_lvl):
        """ Connect threaded agent to server
        Args:
            feat_lvl: Feature level to use. ('high', 'low', 'simple')
            base: Which base to launch agent to. ('left', 'right)
            goalie: Play goalie. (True, False)
            agent_ID: Integer representing agent index. (0-11)
        Returns:
            None, thread runs on server continually.
        """


        if feat_lvl == 'low':
            feat_lvl = hfo.LOW_LEVEL_FEATURE_SET
        elif feat_lvl == 'high':
            feat_lvl = hfo.HIGH_LEVEL_FEATURE_SET
        elif feat_lvl == 'simple':
            feat_lvl = hfo.SIMPLE_LEVEL_FEATURE_SET

        config_dir=get_config_path() 
        recorder_dir = 'logs/'
        if self.team_base == base:
            self.team_envs[agent_ID].connectToServer(feat_lvl, config_dir=config_dir,
                                server_port=port, server_addr='localhost', team_name=base,
                                                    play_goalie=goalie,record_dir =recorder_dir)
        else:
            self.opp_team_envs[agent_ID].connectToServer(feat_lvl, config_dir=config_dir,
                                server_port=port, server_addr='localhost', team_name=base, 
                                                    play_goalie=goalie,record_dir =recorder_dir)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Once all agents have been loaded,
        # wait for action command, take action, update: obs, reward, and world status
        ep_num = 0

        while(True):
            while(self.start):
                ep_num += 1
                j = 0 # j to maximum episode length

                if self.team_base == base:

                    self.team_obs_previous[agent_ID,:-8] = self.team_envs[agent_ID].getState() # Get initial state
                    self.team_obs[agent_ID,:-8] = self.team_envs[agent_ID].getState() # Get initial state
                    self.team_obs[agent_ID,-8:] = [0.0,0.0,0.0, 0.0,0.0,0.0,0.0,0.0]
                    self.team_obs_previous[agent_ID,-8:] = [0.0,0.0,0.0, 0.0,0.0,0.0,0.0,0.0]
                else:
                    self.opp_team_obs_previous[agent_ID,:-8] = self.opp_team_envs[agent_ID].getState() # Get initial state
                    self.opp_team_obs[agent_ID,:-8] = self.opp_team_envs[agent_ID].getState() # Get initial state
                    self.opp_team_obs[agent_ID,-8:] = [0.0,0.0,0.0, 0.0,0.0,0.0,0.0,0.0]
                    self.opp_team_obs_previous[agent_ID,-8:] = [0.0,0.0,0.0, 0.0,0.0,0.0,0.0,0.0]


                self.been_kicked_team = False
                self.been_kicked_opp = False
                while j < fpt:

                    self.sync_after_queue.wait()

                    
                    # take the action
                    if self.team_base == base:
                        # take the action
                        if act_lvl == 'high':
                            self.team_envs[agent_ID].act(self.action_list[self.team_actions[agent_ID]]) # take the action
                            self.sync_at_status_team[agent_ID] += 1
                        elif act_lvl == 'low':
                            # use params for low level actions
                            
                            # scale action params
                            a = self.team_actions[agent_ID]
                            
                            # with tackle -- outdated
                            """if a == 0:
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][0],self.action_params[agent_ID][1])
                                #print(self.action_list[a],self.action_params[agent_ID][0],self.action_params[agent_ID][1])
                            elif a == 1:
                                #print(self.action_list[a],self.action_params[agent_ID][2])
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][2])
                            elif a == 2:
                                #print(self.action_list[a],self.action_params[agent_ID][3])                            
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][3])           
                            elif a ==3:
                                #print(self.action_list[a],self.action_params[agent_ID][4],self.action_params[agent_ID][5])
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][4],self.action_params[agent_ID][5])
                            """
                            
                            # without tackle
                            if a == 0:
                                self.team_envs[agent_ID].act(self.action_list[a],self.get_valid_scaled_param(agent_ID,0,base),self.get_valid_scaled_param(agent_ID,1,base))
                                #print(self.action_list[a],self.action_params[agent_ID][0],self.action_params[agent_ID][1])
                            elif a == 1:
                                #print(self.action_list[a],self.action_params[agent_ID][2])
                                self.team_envs[agent_ID].act(self.action_list[a],self.get_valid_scaled_param(agent_ID,2,base))                       
                            elif a ==2:
                                #print(self.action_list[a],self.action_params[agent_ID][4],self.action_params[agent_ID][5])
                                self.team_envs[agent_ID].act(self.action_list[a],self.get_valid_scaled_param(agent_ID,3,base),self.get_valid_scaled_param(agent_ID,4,base))

                    else:
                        # take the action
                        if act_lvl == 'high':
                            self.opp_team_envs[agent_ID].act(self.action_list[self.opp_actions[agent_ID]]) # take the action
                            self.sync_at_status_opp[agent_ID] += 1
                        elif act_lvl == 'low':
                            # use params for low level actions
                            # scale action params
                            a = self.opp_actions[agent_ID]
                            
                            # with tackle -- outdated
                            """if a == 0:
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][0],self.action_params[agent_ID][1])
                                #print(self.action_list[a],self.action_params[agent_ID][0],self.action_params[agent_ID][1])
                            elif a == 1:team_envs
                                #print(self.action_list[a],self.action_params[agent_ID][2])
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][2])
                            elif a == 2:
                                #print(self.action_list[a],self.action_params[agent_ID][3])                            
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][3])           
                            elif a ==3:
                                #print(self.action_list[a],self.action_params[agent_ID][4],self.action_params[agent_ID][5])
                                self.team_envs[agent_ID].act(self.action_list[a],self.action_params[agent_ID][4],self.action_params[agent_ID][5])
                            """
                            # without tackle
                            if a == 0:
                                self.opp_team_envs[agent_ID].act(self.action_list[a],self.get_valid_scaled_param(agent_ID,0,base),self.get_valid_scaled_param(agent_ID,1,base))
                                #print(self.action_list[a],self.action_params[agent_ID][0],self.action_params[agent_ID][1])
                            elif a == 1:
                                #print(self.action_list[a],self.action_params[agent_ID][2])
                                self.opp_team_envs[agent_ID].act(self.action_list[a],self.get_valid_scaled_param(agent_ID,2,base))                       
                            elif a == 2:
                                #print(self.action_list[a],self.action_params[agent_ID][4],self.action_params[agent_ID][5])
                                self.opp_team_envs[agent_ID].act(self.action_list[a],self.get_valid_scaled_param(agent_ID,3,base),self.get_valid_scaled_param(agent_ID,4,base))

                    self.sync_at_status.wait()
                    
                    if self.team_base == base:
                        self.team_obs_previous[agent_ID] = self.team_obs[agent_ID]
                        self.world_status = self.team_envs[agent_ID].step() # update world                        
                        self.team_obs[agent_ID,:-8] = self.team_envs[agent_ID].getState() # update obs after all agents have acted
                        self.team_obs[agent_ID,-8:] =  self.team_actions_OH[agent_ID]
                    else:
                        self.opp_team_obs_previous[agent_ID] = self.opp_team_obs[agent_ID]
                        self.world_status = self.opp_team_envs[agent_ID].step() # update world
                        self.opp_team_obs[agent_ID,:-8] = self.opp_team_envs[agent_ID].getState() # update obs after all agents have acted
                        self.opp_team_obs[agent_ID,-8:] =  self.opp_actions_OH[agent_ID]

                    self.sync_at_reward.wait()

                    if self.world_status == hfo.IN_GAME:
                        self.d = 0
                    else:
                        self.d = 1

                    if self.team_base == base:
                        self.team_rewards[agent_ID] = self.getReward(
                            self.team_envs[agent_ID].statusToString(self.world_status),agent_ID,base,ep_num) # update reward
                    else:
                        self.opp_rewards[agent_ID] = self.getReward(
                            self.opp_team_envs[agent_ID].statusToString(self.world_status),agent_ID,base,ep_num) # update reward
                    j+=1
                    self.sync_before_step.wait()


                    # Break if episode done
                    if self.d == True:
                        break

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _start_hfo_server(self):
            """
            Starts the Half-Field-Offense server.
            frames_per_trial: Episodes end after this many steps.
            untouched_time: Episodes end if the ball is untouched for this many steps.
            offense_agents: Number of user-controlled offensive players.
            defense_agents: Number of user-controlled defenders.
            offense_npcs: Number of offensive bots.
            defense_npcs: Number of defense bots.
            sync_mode: Disabling sync mode runs server in real time (SLOW!).
            port: Port to start the server on.
            offense_on_ball: Player to give the ball to at beginning of episode.
            fullstate: Enable noise-free perception.
            seed: Seed the starting positions of the players and ball.
            ball_x_[min/max]: Initialize the ball this far downfield: [-1,1]
            verbose: Verbose server messages.
            log_game: Enable game logging. Logs can be used for replay + visualization.
            log_dir: Directory to place game logs (*.rcg).
            """
            self.server_port = self.port
            cmd = self.hfo_path + \
                  " --headless --frames-per-trial %i --untouched-time %i --offense-agents %i"\
                  " --defense-agents %i --offense-npcs %i --defense-npcs %i"\
                  " --port %i --offense-on-ball %i --seed %i --ball-x-min %f"\
                  " --ball-x-max %f --ball-y-min %f --ball-y-max %f"\
                  " --logs-dir %s --message-size 256"\
                  % (self.fpt, self.untouched, self.num_TA,
                     self.num_OA, self.num_TNPC, self.num_ONPC, self.port,
                     self.offense_on_ball, self.seed, self.config.ball_x_min, self.config.ball_x_max,
                     self.config.ball_y_min, self.config.ball_y_max, self.config.log)
            #Adds the binaries when offense and defense npcs are in play, must be changed to add agent vs binary npc
            if self.num_TNPC > 0:   cmd += " --offense-team %s" \
                % (self.config.left_bin)
            if self.num_ONPC > 0:   cmd += " --defense-team %s" \
                % (self.config.right_bin)
            if not self.config.sync_mode:      cmd += " --no-sync"
            if self.config.fullstate:          cmd += " --fullstate"
            if self.config.determ:      cmd += " --deterministic"
            if self.config.verbose:            cmd += " --verbose"
            if not self.config.rcss_log:  cmd += " --no-logging"
            if self.config.hfo_log:       cmd += " --hfo-logging"
            if self.config.record_lib:             cmd += " --record"
            if self.config.record_serv:      cmd += " --logs-gen-pt"
            if self.config.init_env:
                cmd += " --agents-x-min %f --agents-x-max %f --agents-y-min %f --agents-y-max %f"\
                        " --change-every-x-ep %i --change-agents-x %f --change-agents-y %f"\
                        " --change-balls-x %f --change-balls-y %f --control-rand-init"\
                        % (self.config.agents_x_min, self.config.agents_x_max, self.config.agents_y_min, self.config.agents_y_max,
                            self.config.change_every_x, self.config.change_agents_x, self.config.change_agents_y,
                            self.config.change_ball_x, self.config.change_ball_y)

            print('Starting server with command: %s' % cmd)
            self.server_process = subprocess.Popen(cmd.split(' '), shell=False)
            time.sleep(3) # Wait for server to startup before connecting a player

    def _start_viewer(self):
        """
        Starts the SoccerWindow visualizer. Note the viewer may also be
        used with a *.rcg logfile to replay a game. See details at
        https://github.com/LARG/HFO/blob/master/doc/manual.pdf.
        """
        
        if self.viewer is not None:
            os.kill(self.viewer.pid, signal.SIGKILL)
        cmd = get_viewer_path() +\
              " --connect --port %d" % (self.server_port)
        self.viewer = subprocess.Popen(cmd.split(' '), shell=False)

