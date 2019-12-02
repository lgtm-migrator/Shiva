from .Agent import Agent
import copy
import numpy as np
from networks.DynamicLinearNetwork import DynamicLinearNetwork, SoftMaxHeadDynamicLinearNetwork

class ParametrizedDDPGAgent(Agent):
    def __init__(self, id, obs_dim, action_dim, param_ix, agent_config: dict, networks: dict):
        super(ParametrizedDDPGAgent, self).__init__(id, obs_dim, action_dim, agent_config, networks)
        self.id = id

        self.actor = SoftMaxHeadDynamicLinearNetwork(obs_dim, action_dim, param_ix, networks['actor'])
        self.target_actor = copy.deepcopy(self.actor)

        self.critic = DynamicLinearNetwork(obs_dim + action_dim, 1, networks['critic'])
        self.target_critic = copy.deepcopy(self.critic)

        self.actor_optimizer = self.optimizer_function(params=self.actor.parameters(), lr=self.learning_rate)
        self.critic_optimizer = self.optimizer_function(params=self.critic.parameters(), lr=self.learning_rate)

    def get_action(self, observation):
        return self.actor(observation)

        # Uncomment to check the networks

        # print(self.actor)

        # print(self.critic)

        # input()


    def find_best_imitation_action(self, observation: np.ndarray) -> np.ndarray:

            observation = torch.tensor(observation).to(self.device)
            action = self.actor(observation.float()).cpu().data.numpy()
            action = np.clip(action, -1,1)
            # print('actor action shape', action.shape)
            return action[0]
