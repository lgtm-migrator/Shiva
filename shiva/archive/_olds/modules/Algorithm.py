import random
import numpy as np
import torch
import helpers

def initialize_algorithm(observation_space: int, action_space: int, _params: list):

    if _params[0]['algorithm'] == 'DQN':
        return DQAlgorithm(
            observation_space = observation_space,
            action_space = action_space,
            loss_function = getattr(torch.nn, _params[0]['loss_function']),
            regularizer = _params[0]['regularizer'],
            recurrence = _params[0]['recurrence'],
            optimizer = getattr(torch.optim, _params[0]['optimizer']),
            gamma = float(_params[0]['gamma']),
            learning_rate = float(_params[0]['learning_rate']),
            beta = _params[0]['beta'],
            epsilon = (float(_params[0]['epsilon_start']), float(_params[0]['epsilon_end']), float(_params[0]['epsilon_decay'])),
            C = _params[0]['c'],
            configs = {
                'agent': _params[1],
                'network': _params[2]
            }
        )
    elif _params[0]['algorithm'] == 'Imitation':
        return SupervisedAlgorithm(
        observation_space = observation_space,
        action_space = action_space,
        loss_function = getattr(torch.nn, _params[0]['loss_function']),
        regularizer = _params[0]['regularizer'],
        recurrence = _params[0]['recurrence'],
        optimizer = getattr(torch.optim, _params[0]['optimizer']),
        gamma = float(_params[0]['gamma']),
        learning_rate = float(_params[0]['learning_rate']),
        beta = _params[0]['beta'],
        epsilon = (float(_params[0]['epsilon_start']), float(_params[0]['epsilon_end']), float(_params[0]['epsilon_decay'])),
        C = _params[0]['c'],
        configs = {
            'agent': _params[1],
            'network': _params[2]
        }
        ), DaggerAlgorithm(
        observation_space = observation_space,
        action_space = action_space,
        loss_function = getattr(torch.nn, _params[0]['loss_function']),
        regularizer = _params[0]['regularizer'],
        recurrence = _params[0]['recurrence'],
        optimizer = getattr(torch.optim, _params[0]['optimizer']),
        gamma = float(_params[0]['gamma']),
        learning_rate = float(_params[0]['learning_rate']),
        beta = _params[0]['beta'],
        epsilon = (float(_params[0]['epsilon_start']), float(_params[0]['epsilon_end']), float(_params[0]['epsilon_decay'])),
        C = _params[0]['c'],
        configs = {
            'agent': _params[1],
            'network': _params[2]
        }
        )
    else:
        return None

class AbstractAlgorithm():
    def __init__(self,
        observation_space: np.ndarray,
        action_space: np.ndarray,
        loss_function: object,
        regularizer: object,
        recurrence: bool,
        optimizer_function: object,
        gamma: np.float,
        learning_rate: np.float,
        beta: np.float,
        configs: dict
        ):
        '''
            Input
                observation_space   Shape of the observation space, aka input to policy network
                action_space        Shape of the action space, aka output from policy network
                loss_function       Function used to calculate the loss during training
                regularizer
                recurrence
                optimizer           Optimization function to train network weights
                gamma               Hyperparameter
                learning_rate       Learning rate used in the optimizer
                beta                Hyperparameter
        '''
        self.observation_space = observation_space
        self.action_space = action_space
        self.loss_function = loss_function
        self.regularizer = regularizer
        self.recurrence = recurrence
        self.optimizer_function = optimizer_function
        self.gamma = gamma
        self.learning_rate = learning_rate
        self.beta = beta
        self.configs = configs


        self.loss_calc = self.loss_function()
        self.agents = []
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    def update(self, agent, data):
        '''
            Updates the agents network using the data

            Input
                agent:  the agent who we want to update it's network
                data:   data used to train the network

            Return
                None
        '''
        pass

    def get_action(self, agent, observation):
        '''
            Determines the best action for the agent and a given observation

            Input
                agent:          the agent we want the action
                observation:

            Return
                Action
        '''
        pass

    def create_agent(self):
        '''
            Creates a new agent

            Input

            Return
                Agent
        '''
        pass

    def get_agents(self):
        return self.agents

##########################################################################
#    DQ Algorithm Implementation
#
#    Discrete Action Space
##########################################################################

from Agent import DQAgent

# average loss per episode
# loss per step

class DQAlgorithm(AbstractAlgorithm):
    def __init__(self,
        observation_space: int,
        action_space: int,
        loss_function: object,
        regularizer: object,
        recurrence: bool,
        optimizer: object,
        gamma: np.float,
        learning_rate: np.float,
        beta: np.float,
        epsilon: set(),
        C: int,
        configs: dict):
        '''
            Inputs
                epsilon        (start, end, decay rate), example: (1, 0.02, 10**5)
                C              Number of iterations before the target network is updated
        '''
        super(DQAlgorithm, self).__init__(observation_space, action_space, loss_function, regularizer, recurrence, optimizer, gamma, learning_rate, beta, configs)
        self.epsilon_start = epsilon[0]
        self.epsilon_end = epsilon[1]
        self.epsilon_decay = epsilon[2]
        self.C = C
        
        self.totalLoss = 0
        self.loss = 0

    def update(self, agent, minibatch, step_n):
        '''
            Implementation
                1) Calculate what the current expected Q val from each sample on the replay buffer would be
                2) Calculate loss between current and past reward
                3) Optimize
                4) If agent steps reached C, update agent.target network

            Input
                agent       Agent who we are updating
                minibatch   Batch from the experience replay buffer

            Returns
                None
        '''

        states, actions, rewards, next_states, dones = minibatch
        # make tensors as needed
        # states_v = torch.tensor(states).float().to(self.device)
        # next_states_v = torch.tensor(next_states).float().to(self.device)
        # actions_v = torch.tensor(actions).to(self.device)
        rewards_v = torch.tensor(rewards).to(self.device)
        done_mask = torch.tensor(dones, dtype=torch.bool).to(self.device)

        agent.optimizer.zero_grad()
        # 1) GRAB Q_VALUE(s_j, a_j) from minibatch
        input_v = torch.tensor([ np.concatenate([s_i, a_i]) for s_i, a_i in zip(states, actions) ]).float().to(self.device)
        state_action_values = agent.policy(input_v)
        # 2) GRAB MAX[Q_HAT_VALUES(s_j+1)]
        # For the observations s_j+1, select an action using the Policy and calculate Q values of those using the Target net
        input_v = torch.tensor([ np.concatenate([s_i, agent.get_action_target(s_i) ]) for s_i in next_states ]).float().to(self.device)
        next_state_values = agent.target_policy(input_v)
        # 3) Overwrite 0 on all next_state_values where they were termination states
        next_state_values[done_mask] = 0.0
        # 4) Detach magic
        # We detach the value from its computation graph to prevent gradients from flowing into the neural network used to calculate Q approximation next states.
        # Without this our backpropagation of the loss will start to affect both predictions for the current state and the next state.
        next_state_values = next_state_values.detach()

        expected_state_action_values = next_state_values * self.gamma + rewards_v

        loss_v = self.loss_calc(state_action_values, expected_state_action_values)

        self.totalLoss += loss_v
        self.loss = loss_v

        loss_v.backward()
        agent.optimizer.step()

        if step_n % self.C == 0:
            agent.target_policy.load_state_dict(agent.policy.state_dict()) # Assuming is PyTorch!
    
    def get_action(self, agent, observation, step_n) -> np.ndarray:
        '''
            With the probability epsilon we take the random action,
            otherwise we use the network to obtain the best Q-value per each action
        '''
        epsilon = max(self.epsilon_end, self.epsilon_start - (step_n / self.epsilon_decay))
        if random.uniform(0, 1) < epsilon:
            action_idx = random.sample(range(self.action_space), 1)[0]
            action = helpers.action2one_hot(self.action_space, action_idx)
        else:
            # Iterate over all the actions to find the highest Q value
            action = agent.get_action(observation)
        return action # replay buffer store lists and env does np.argmax(action)

    def get_loss(self):
        return self.loss

    def get_average_loss(self, step):
        average = self.totalLoss/step
        self.totalLoss = 0
        return average

    def create_agent(self, id):
        new_agent = DQAgent(id, self.observation_space, self.action_space, self.optimizer_function, self.learning_rate, self.configs)
        self.agents.append(new_agent)
        return new_agent

    def create_empty_agent(self):
        pass


##########################################################################
#    DDPG Algorithm Implementation
#
##########################################################################

class DDPGAlgorithm(AbstractAlgorithm):
    def __init__(self,
        observation_space: int,
        action_space: int,
        loss_function: object,
        regularizer: object,
        recurrence: bool,
        optimizer: object,
        gamma: np.float,
        learning_rate: np.float,
        beta: np.float,
        epsilon: set(),
        C: int,
        configs: dict):
        '''
            Inputs
                epsilon        (start, end, decay rate), example: (1, 0.02, 10**5)
                C              Number of iterations before the target network is updated
        '''
        super(DQAlgorithm, self).__init__(observation_space, action_space, loss_function, regularizer, recurrence, optimizer, gamma, learning_rate, beta, configs)
        self.epsilon_start = epsilon[0]
        self.epsilon_end = epsilon[1]
        self.epsilon_decay = epsilon[2]
        self.C = C

    def update(self, agent, minibatch, step_n):
        pass

    def create_agent(self, id):
        new_agent = DDPGAgent(id, self.observation_space, self.action_space, self.optimizer_function, self.learning_rate, self.configs)
        self.agents.append(new_agent)
        return new_agent


###############################################################################
#
#Supervised Algorithm Implementation
#
###############################################################################
from Agent import ImitationAgent

class SupervisedAlgorithm(AbstractAlgorithm):
    def __init__(self,
        observation_space: int,
        action_space: int,
        loss_function: object,
        regularizer: object,
        recurrence: bool,
        optimizer: object,
        gamma: np.float,
        learning_rate: np.float,
        beta: np.float,
        epsilon: set(),
        C: int,
        configs: dict):
        '''
            Inputs
                epsilon        (start, end, decay rate), example: (1, 0.02, 10**5)
                C              Number of iterations before the target network is updated
        '''
        super(SupervisedAlgorithm, self).__init__(observation_space, action_space, loss_function, regularizer, recurrence, optimizer, gamma, learning_rate, beta, configs)
        self.C = C
    def update(self, agent, minibatch, step_n):
        '''
            Implementation
                1) Collect trajectories from the expert agent on a replay buffer
                2) Calculate the Cross Entropy Loss between imitation agent and
                    expert agent actions
                3) Optimize

            Input
                agent       Agent who we are updating
                minibatch   Batch from the experience replay buffer

            Returns
                None
        '''
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        states, actions, rewards, next_states, dones = minibatch

        rewards_v = torch.tensor(rewards).to(device)
        done_mask = torch.ByteTensor(dones).to(device)

        # zero optimizer
        agent.optimizer.zero_grad()

        #input_v = torch.tensor([ np.concatenate([s_i, a_i]) for s_i, a_i in zip(states, actions) ]).float().to(device)
        input_v = torch.tensor(states).float().to(device)
        state_action_values = agent.policy(input_v).to(device) #.gather(1, actions_v.unsqueeze(-1)).squeeze(-1)
        #expert_state_action_values = expert_agent.policy(input_v)

        #next_state_values[done_mask] = 0.0
        # 4) Detach magic
        # We detach the value from its computation graph to prevent
        # gradients from flowing into the neural network used to calculate Q
        # approximation for next states.
        # Without this our backpropagation of the loss will start to affect both
        # predictions for the current state and the next state.
        #next_state_values = next_state_values.detach()

        #Loss will be the loss between the imitation agent approximated values,
        #and the expert agent approximated values.
        loss_v = self.loss_calc(state_action_values, rewards).to(device)
        loss_v.backward().to(device)
        agent.optimizer.step().to(device)



    def get_action(self, agent, observation, step_n) -> np.ndarray:

        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        obs_v = torch.tensor(observation).to(device)
        best_act = action2one_hot(np.argmax(agent.policy(obs_v)))

        return best_act.tolist()

    def create_agent(self,root,id):
        new_agent = ImitationAgent(self.observation_space, self.action_space, self.optimizer_function, self.learning_rate,root,id, self.configs)
        self.agents.append(new_agent)
        return new_agent

    def get_loss(self):
        return self.loss

    def get_average_loss(self, step):
        average = self.totalLoss/step
        self.totalLoss = 0
        return average




###############################################################################
#
# Dagger Algorithm for Imitation Implementation
#
################################################################################

class DaggerAlgorithm(AbstractAlgorithm):
    def __init__(self,
        observation_space: int,
        action_space: int,
        loss_function: object,
        regularizer: object,
        recurrence: bool,
        optimizer: object,
        gamma: np.float,
        learning_rate: np.float,
        beta: np.float,
        epsilon: set(),
        C: int,
        configs: dict):

        super(DaggerAlgorithm, self).__init__(observation_space, action_space, loss_function, regularizer, recurrence, optimizer, gamma, learning_rate, beta, configs)
        self.C = C

    def update(self, imitation_agent,expert_agent, minibatch, step_n):
        '''
            Implementation
                1) Collect Trajectories from the imitation policy
                2) Calculate the Cross Entropy Loss between the imitation policy's
                    actions and the actions the expert policy would have taken.
                3) Optimize

            Input
                agent       Agent who we are updating
                minibatch   Batch from the experience replay buffer

            Returns
                None
        '''
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        states, actions, rewards, next_states, dones = minibatch

        rewards_v = torch.tensor(rewards).to(device)
        done_mask = torch.ByteTensor(dones).to(device)

        # zero optimizer
        agent.optimizer.zero_grad()

        input_v = torch.tensor(states).float().to(device)
        state_action_prob_dist= imitation_agent.policy(input_v).to(device) #.gather(1, actions_v.unsqueeze(-1)).squeeze(-1)
        expert_action = expert_agent.policy(input_v)


        #Loss will be Cross Entropy Loss between the action probabilites produced
        #by the imitation agent, and the action took by the expert.
        loss_v = self.loss_calc(state_action_prob_dist, expert_action).to(device)
        loss_v.backward().to(device)
        imitation_agent.optimizer.step().to(device)

        def get_action(self, agent, observation, step_n) -> np.ndarray:

            device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

            obs_v = torch.tensor(observation).to(device)
            best_act = action2one_hot(np.argmax(agent.policy(obs_v)))

            return best_act.tolist()# replay buffer store lists and env does np.argmax(action)


        def action2one_hot(self, action_idx: int) -> np.ndarray:
            z = np.zeros(self.action_space)
            z[action_idx] = 1
            return z

        def get_loss(self):
            return self.loss

        def get_average_loss(self, step):
            average = self.totalLoss/step
            self.totalLoss = 0
            return average
