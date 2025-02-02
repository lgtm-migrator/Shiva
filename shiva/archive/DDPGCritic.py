import torch
import torch.nn as nn

from shiva.helpers import networks_handler as nh

class DDPGCritic(torch.nn.Module):
    def __init__(self, obs_dim, action_dim, head_config, tail_config):
        super(DDPGCritic, self).__init__()
        torch.manual_seed(5)
        
        self.net_head = nh.DynamicLinearSequential(obs_dim, 
                                                400, 
                                                head_config['layers'], 
                                                nh.parse_functions(torch.nn, head_config['activation_function']), 
                                                head_config['last_layer'], 
                                                head_config['output_function'])
                                                
        self.net_tail = nh.DynamicLinearSequential(action_dim + 400, 
                                                1, 
                                                tail_config['layers'], 
                                                nh.parse_functions(torch.nn, tail_config['activation_function']), 
                                                tail_config['last_layer'],
                                                tail_config['output_function'])
    
    def forward(self, x, a):
        obs = self.net_head(x)
        # print(a.shape)
        # print(obs.shape)
        return self.net_tail(torch.cat([obs, a], dim=1))