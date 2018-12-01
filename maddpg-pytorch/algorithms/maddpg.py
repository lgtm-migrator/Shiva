import torch
import torch.nn.functional as F
from utils.networks import MLPNetwork_Actor,MLPNetwork_Critic
from utils.misc import soft_update, average_gradients, onehot_from_logits, gumbel_softmax,hard_update
from utils.agents import DDPGAgent
from utils.misc import distr_projection
import numpy as np
from torch.autograd import Variable

MSELoss = torch.nn.MSELoss()
CELoss = torch.nn.CrossEntropyLoss()

class MADDPG(object):
    """
    Wrapper class for DDPG-esque (i.e. also MADDPG) agents in multi-agent task
    """
    def __init__(self, team_agent_init_params, opp_agent_init_params, team_alg_types, opp_alg_types,
                 gamma=0.95, batch_size=0,tau=0.01, a_lr=0.01, c_lr=0.01, hidden_dim=64,
                 discrete_action=True,vmax = 10,vmin = -10, N_ATOMS = 51, n_steps = 5,
                 DELTA_Z = 20.0/50,D4PG=False,beta = 0,TD3=False,TD3_noise = 0.2,TD3_delay_steps=2,
                 I2A = False,EM_lr = 0.001,obs_weight=10.0,rew_weight=1.0,ws_weight=1.0,rollout_steps = 5,LSTM_hidden=64):
        """
        Inputs:
            agent_init_params (list of dict): List of dicts with parameters to
                                              initialize each agent
                num_in_pol (int): Input dimensions to policy
                num_out_pol (int): Output dimensions to policy
                num_in_critic (int): Input dimensions to critic
            alg_types (list of str): Learning algorithm for each agent (DDPG
                                       or MADDPG)
            gamma (float): Discount factor
            tau (float): Target update rate
            lr (float): Learning rate for policy and critic
            hidden_dim (int): Number of hidden dimensions for networks
            discrete_action (bool): Whether or not to use discrete action space
        """
        self.world_status_dim = 6 # number of possible world statuses
        self.nagents_team = len(team_alg_types)
        self.nagents_opp = len(opp_alg_types)

        self.team_alg_types = team_alg_types
        self.opp_alg_types = opp_alg_types

        self.team_agents = [DDPGAgent(discrete_action=discrete_action,
                                 hidden_dim=hidden_dim,a_lr=a_lr, c_lr=c_lr,
                                 n_atoms = N_ATOMS, vmax = vmax, vmin = vmin,
                                 delta = DELTA_Z,D4PG=D4PG,
                                 TD3=TD3,
                                 I2A = I2A,EM_lr=EM_lr,
                                 world_status_dim=self.world_status_dim,rollout_steps = rollout_steps,LSTM_hidden=LSTM_hidden,
                                 **params)
                       for params in team_agent_init_params]
        
        self.opp_agents = [DDPGAgent(discrete_action=discrete_action,
                                 hidden_dim=hidden_dim,a_lr=a_lr, c_lr=c_lr,
                                 n_atoms = N_ATOMS, vmax = vmax, vmin = vmin,
                                 delta = DELTA_Z,D4PG=D4PG,
                                 TD3=TD3,
                                 I2A = I2A,EM_lr=EM_lr,
                                 world_status_dim=self.world_status_dim,rollout_steps = rollout_steps,LSTM_hidden=LSTM_hidden,
                                 **params)
                       for params in opp_agent_init_params]

        self.team_agent_init_params = team_agent_init_params
        self.opp_agent_init_params = opp_agent_init_params

        self.gamma = gamma
        self.batch_size = batch_size
        self.tau = tau
        self.a_lr = a_lr
        self.c_lr = c_lr
        self.discrete_action = discrete_action
        self.pol_dev = 'cpu'  # device for policies
        self.critic_dev = 'cpu'  # device for critics
        self.trgt_pol_dev = 'cpu'  # device for target policies
        self.trgt_critic_dev = 'cpu'  # device for target critics
        self.niter = 0
        self.n_steps = n_steps
        self.beta = beta
        self.N_ATOMS = N_ATOMS
        self.Vmax = vmax
        self.Vmin = vmin
        self.DELTA_Z = DELTA_Z
        self.D4PG = D4PG
        self.TD3 = TD3
        self.TD3_noise = TD3_noise
        self.TD3_delay_steps = TD3_delay_steps
        if not TD3:
            self.TD3_delay_steps = 1
        self.EM_lr = EM_lr
        self.I2A = I2A
        self.obs_weight = obs_weight
        self.rew_weight = rew_weight
        self.ws_weight = ws_weight
        self.ws_onehot = torch.FloatTensor(self.batch_size,self.world_status_dim)
        self.count = 0

    @property
    def team_policies(self):
        return [a.policy for a in self.team_agents]
    
    @property
    def opp_policies(self):
        return [a.policy for a in self.opp_agents]

    @property
    def team_target_policies(self):
        return [a.target_policy for a in self.team_agents]

    @property
    def opp_target_policies(self):
        return [a.target_policy for a in self.opp_agents]
    
    def scale_beta(self, beta):
        """
        Scale beta
        Inputs:
            scale (float): scale of beta
        """
        self.beta = beta

    
    def scale_noise(self, scale):
        """
        Scale noise for each agent
        Inputs:
            scale (float): scale of noise
        """
        for a in self.team_agents:
            a.scale_noise(scale)

        for a in self.opp_agents:
            a.scale_noise(scale)

    def reset_noise(self):
        for a in self.team_agents:
            a.reset_noise()
        
        for a in self.opp_agents:
            a.reset_noise()

    def step(self, team_observations, opp_observations, explore=False):
        """
        Take a step forward in environment with all agents
        Inputs:
            observations: List of observations for each agent
            explore (boolean): Whether or not to add exploration noise
        Outputs:
            actions: List of actions for each agent
        """
        return [a.step(obs, explore=explore) for a, obs in zip(self.team_agents, team_observations)], \
                [a.step(obs, explore=explore) for a, obs in zip(self.opp_agents, opp_observations)]
    
    
    def discrete_param_indices(self,discrete):
        if discrete == 0:
            return [0,1]
        elif discrete == 1:
            return [2]
        if discrete == 2:
            return [3,4]
                     
                     
    # zeros the params corresponding to the non-chosen actions
    def zero_params(self,params,actions_oh):
        for a,p in zip(actions_oh,params):
            if np.argmax(a.data.numpy()) == 0:
                p[2 + len(a)] = 0 # offset by num of actions to get params
                p[3 + len(a)] = 0
                p[4 + len(a)] = 0
            if np.argmax(a.data.numpy()) == 1:
                p[0 + len(a)] = 0
                p[1 + len(a)] = 0
                p[3 + len(a)] = 0
                p[4 + len(a)] = 0
            if np.argmax(a.data.numpy()) == 2:
                p[0 + len(a)] = 0
                p[1 + len(a)] = 0
                p[2 + len(a)] = 0
        return params


    def update(self, sample, agent_i, side, parallel=False, logger=None):
        """
        Update parameters of agent model based on sample from replay buffer
        Inputs:
            sample: tuple of (observations, actions, rewards, next
                    observations, and episode end masks, cumulative discounted reward) sampled randomly from
                    the replay buffer. Each is a list with entries
                    corresponding to each agent
            agent_i (int): index of agent to update
            parallel (bool): If true, will average gradients across threads
            logger (SummaryWriter from Tensorboard-Pytorch):
                If passed in, important quantities will be logged
        """
        # rews = 1-step, cum-rews = n-step
        obs, acs, rews, next_obs, dones,MC_rews,n_step_rews,ws = sample
        if side == 'team':
            curr_agent = self.team_agents[agent_i]
        else:
            curr_agent = self.opp_agents[agent_i]
        zero_values = False
        
        # Train critic ------------------------
        curr_agent.critic_optimizer.zero_grad()
        
        if zero_values:
            if side == 'team':
                all_trgt_acs = [torch.cat( # concat one-hot actions with params (that are zero'd along the indices of the non-chosen actions)
                (onehot_from_logits(pi(nobs)[:,:curr_agent.action_dim]),
                self.zero_params(pi(nobs),onehot_from_logits(pi(nobs)[:,:curr_agent.action_dim]))[:,curr_agent.action_dim:]),1)
                            for pi, nobs in zip(self.team_target_policies, next_obs)]    # onehot the action space but not param
                if self.TD3:
                    noise = torch.randn_like(acs)*self.TD3_noise
                    all_trgt_acs = [torch.cat( # concat one-hot actions with params (that are zero'd along the indices of the non-chosen actions)
                        (onehot_from_logits((pi(nobs) + noise)[:,:curr_agent.action_dim]),
                        self.zero_params((pi(nobs)+noise),onehot_from_logits((pi(nobs)+noise)[:,:curr_agent.action_dim]))[:,curr_agent.action_dim:]),1)
                            for pi, nobs in zip(self.team_target_policies, next_obs)]    # onehot the action space but not param
            else:
                all_trgt_acs = [torch.cat( # concat one-hot actions with params (that are zero'd along the indices of the non-chosen actions)
                (onehot_from_logits(pi(nobs)[:,:curr_agent.action_dim]),
                self.zero_params(pi(nobs),onehot_from_logits(pi(nobs)[:,:curr_agent.action_dim]))[:,curr_agent.action_dim:]),1)
                            for pi, nobs in zip(self.opp_target_policies, next_obs)]    # onehot the action space but not param
                if self.TD3:
                    noise = torch.randn_like(acs)*self.TD3_noise
                    all_trgt_acs = [torch.cat( # concat one-hot actions with params (that are zero'd along the indices of the non-chosen actions)
                        (onehot_from_logits((pi(nobs) + noise)[:,:curr_agent.action_dim]),
                        self.zero_params((pi(nobs)+noise),onehot_from_logits((pi(nobs)+noise)[:,:curr_agent.action_dim]))[:,curr_agent.action_dim:]),1)
                            for pi, nobs in zip(self.opp_target_policies, next_obs)]    # onehot the action space but not param
        else:
            if side == 'team':
                if self.TD3:
                    noise = torch.randn_like(acs[0]) * self.TD3_noise
                    all_trgt_acs = [pi(nobs) + noise for pi, nobs in zip(self.team_target_policies,next_obs)]                  
                else:
                    all_trgt_acs = [pi(nobs) for pi, nobs in zip(self.team_target_policies,next_obs)]
            else:
                if self.TD3:
                    noise = torch.randn_like(acs[0]) * self.TD3_noise
                    all_trgt_acs = [pi(nobs) + noise for pi, nobs in zip(self.opp_target_policies,next_obs)]                  
                else:
                    all_trgt_acs = [pi(nobs) for pi, nobs in zip(self.opp_target_policies,next_obs)]
            
            

        # Target critic values
        trgt_vf_in = torch.cat((*next_obs, *all_trgt_acs), dim=1)
        if self.TD3: # TODO* For D4PG case, need mask with indices of the distributions whos distr_to_q(trgtQ1) < distr_to_q(trgtQ2)
                     # and build the combination of distr choosing the minimums
            trgt_Q1,trgt_Q2 = curr_agent.target_critic(trgt_vf_in)
            if self.D4PG:
                arg = np.argmin([curr_agent.target_critic.distr_to_q(trgt_Q1).mean().data.numpy(),
                                 curr_agent.target_critic.distr_to_q(trgt_Q2).mean().data.numpy()])
                if arg: 
                    trgt_Q = trgt_Q1
                else:
                    trgt_Q = trgt_Q2
            else:
                trgt_Q = torch.min(trgt_Q1,trgt_Q2)
        else:
            trgt_Q = curr_agent.target_critic(trgt_vf_in)
        # Actual critic values
        vf_in = torch.cat((*obs, *acs), dim=1)
        if self.TD3:
            actual_value_1, actual_value_2 = curr_agent.critic(vf_in)
        else:
            actual_value = curr_agent.critic(vf_in)
        
        if self.D4PG:
                # Q1
                trgt_vf_distr = F.softmax(trgt_Q,dim=1) # critic distribution
                trgt_vf_distr_proj = distr_projection(self,trgt_vf_distr,n_step_rews[agent_i],dones[agent_i],MC_rews[agent_i],
                                                  gamma=self.gamma**self.n_steps,device='cpu')
                if self.TD3:
                    prob_dist_1 = -F.log_softmax(actual_value_1,dim=1) * trgt_vf_distr_proj # Q1
                    prob_dist_2 = -F.log_softmax(actual_value_2,dim=1) * trgt_vf_distr_proj # Q2
                    # distribution distance function
                    vf_loss = prob_dist_1.sum(dim=1).mean() + prob_dist_2.sum(dim=1).mean() # critic loss based on distribution distance
                else:
                    prob_dist = -F.log_softmax(actual_value,dim=1) * trgt_vf_distr_proj
                    trgt_vf_distr = F.softmax(trgt_Q,dim=1) # critic distribution
                    trgt_vf_distr_proj = distr_projection(self,trgt_vf_distr,n_step_rews[agent_i],dones[agent_i],MC_rews[agent_i],
                                                      gamma=self.gamma**self.n_steps,device='cpu') 
                    # distribution distance function
                    prob_dist = -F.log_softmax(actual_value,dim=1) * trgt_vf_distr_proj
                    vf_loss = prob_dist.sum(dim=1).mean() # critic loss based on distribution distance
        else: # single critic value
            target_value = (1-self.beta)*(n_step_rews[agent_i].view(-1, 1) + (self.gamma**self.n_steps) *
                        trgt_Q * (1 - dones[agent_i].view(-1, 1))) + self.beta*(MC_rews[agent_i].view(-1,1))
            target_value.detach()
            if self.TD3: # handle double critic
                vf_loss = F.mse_loss(actual_value_1, target_value) + F.mse_loss(actual_value_2,target_value)
            else:
                vf_loss = F.mse_loss(actual_value, target_value)

                
            
        vf_loss.backward() 
        if parallel:
            average_gradients(curr_agent.critic)
        torch.nn.utils.clip_grad_norm_(curr_agent.critic.parameters(), 1)
        curr_agent.critic_optimizer.step()
        curr_agent.policy_optimizer.zero_grad()
        
        # Train actor -----------------------
        if self.count % self.TD3_delay_steps == 0:
            if self.discrete_action:
                # Forward pass as if onehot (hard=True) but backprop through a differentiable
                # Gumbel-Softmax sample. The MADDPG paper uses the Gumbel-Softmax trick to backprop
                # through discrete categorical samples, but I'm not sure if that is
                # correct since it removes the assumption of a deterministic policy for
                # DDPG. Regardless, discrete policies don't seem to learn properly without it.
                curr_pol_out = curr_agent.policy(obs[agent_i])
                curr_pol_vf_in = gumbel_softmax(curr_pol_out, hard=True)
            else:
                curr_pol_out = curr_agent.policy(obs[agent_i]) # uses gumbel across the actions

                self.curr_pol_out = curr_pol_out.clone() # for inverting action space
                #gumbel = gumbel_softmax(torch.softmax(curr_pol_out[:,:curr_agent.action_dim].clone()),hard=True)
                #log_pol_out = curr_pol_out[:,:curr_agent.action_dim].clone()

                #gumbel = gumbel_softmax((curr_pol_out[:,:curr_agent.action_dim].clone()),hard=True)

                #log_pol_out = torch.log(curr_pol_out[:,:curr_agent.action_dim].clone())
                #gumbel = gumbel_softmax(log_pol_out,hard=True)
                #gumbel = onehot_from_logits(log_pol_out,eps=0.0)


                # concat one-hot actions with params zero'd along indices non-chosen actions
                if zero_values:
                    curr_pol_vf_in = torch.cat((gumbel, 
                                          self.zero_params(curr_pol_out,gumbel)[:,curr_agent.action_dim:]),1)
                else:
                    curr_pol_vf_in = curr_pol_out

                #print(curr_pol_vf_in)
            all_pol_acs = []
            if side == 'team':
                for i, pi, ob in zip(range(self.nagents_team), self.team_policies, obs):
                    if i == agent_i:
                        all_pol_acs.append(curr_pol_vf_in)
                    elif self.discrete_action:
                        all_pol_acs.append(onehot_from_logits(pi(ob)))
                    else: # shariq does not gumbel this, we don't want to sample noise from other agents actions?
                        a = pi(ob)
                        # g = onehot_from_logits(torch.log(a[:,:curr_agent.action_dim]),hard=True)
                        # c = torch.cat((g,self.zero_params(a,g)[:,curr_agent.action_dim:]),1)
                        all_pol_acs.append(a)
            else:
                for i, pi, ob in zip(range(self.nagents_opp), self.opp_policies, obs):
                    if i == agent_i:
                        all_pol_acs.append(curr_pol_vf_in)
                    elif self.discrete_action:
                        all_pol_acs.append(onehot_from_logits(pi(ob)))
                    else: # shariq does not gumbel this, we don't want to sample noise from other agents actions?
                        a = pi(ob)
                        # g = onehot_from_logits(torch.log(a[:,:curr_agent.action_dim]),hard=True)
                        # c = torch.cat((g,self.zero_params(a,g)[:,curr_agent.action_dim:]),1)
                        all_pol_acs.append(a)

            vf_in = torch.cat((*obs, *all_pol_acs), dim=1)
            # invert gradient --------------------------------------
            self.params = vf_in.data
            self.param_dim = curr_agent.param_dim
            hook = vf_in.register_hook(self.inject)
            # ------------------------------------------------------
            if self.D4PG:
                critic_out = curr_agent.critic.Q1(vf_in)
                distr_q = curr_agent.critic.distr_to_q(critic_out)
                pol_loss = -distr_q.mean()
            else: # non-distributional
                pol_loss = -curr_agent.critic.Q1(vf_in).mean()
            #pol_loss += (curr_pol_out[:curr_agent.action_dim]**2).mean() * 1e-2 # regularize size of action
            pol_loss.backward(retain_graph=True)
            if parallel:
                average_gradients(curr_agent.policy)
            torch.nn.utils.clip_grad_norm_(curr_agent.policy.parameters(), 1) # do we want to clip the gradients?
            curr_agent.policy_optimizer.step()
            hook.remove()
            

        # I2A --------------------------------------
        if self.I2A:
            # Update policy prime
            curr_agent.policy_prime_optimizer.zero_grad()
            curr_pol_out = curr_agent.policy(obs[agent_i])
            # We take the loss between the current policy's behavior and policy prime which is estimating the current policy
            pol_prime_out = curr_agent.policy_prime(obs[agent_i]) # uses gumbel across the actions
            pol_prime_out_actions = pol_prime_out[:,:curr_agent.action_dim].float()
            pol_prime_out_params = pol_prime_out[:,curr_agent.action_dim:]
            pol_out_actions = curr_pol_out[:,:curr_agent.action_dim].float()
            pol_out_params = curr_pol_out[:,curr_agent.action_dim:]
            target_classes = torch.argmax(pol_out_actions,dim=1) # categorical integer for predicted class
            MSE =np.sum([F.mse_loss(prime[self.discrete_param_indices(target_class)],current[self.discrete_param_indices(target_class)]) for prime,current,target_class in zip(pol_prime_out_params,pol_out_params, target_classes)])
            #pol_loss = MSE + CELoss(pol_out_actions,target_classes)
            pol_prime_loss = MSE + F.mse_loss(pol_prime_out_actions,pol_out_actions)
            pol_prime_loss.backward()
            if parallel:
                average_gradients(curr_agent.policy_prime)
            torch.nn.utils.clip_grad_norm_(curr_agent.policy_prime.parameters(), 1) # do we want to clip the gradients?
            curr_agent.policy_prime_optimizer.step()

            # Train Environment Model -----------------------------------------------------            
            curr_agent.EM_optimizer.zero_grad()
            
            labels = ws[0].long().view(-1,1) % self.world_status_dim # categorical labels for OH
            self.ws_onehot.zero_() # reset OH tensor
            self.ws_onehot.scatter_(1,labels,1) # fill with OH encoding
            EM_in = torch.cat((*obs, *acs),dim=1)
            est_obs_diff,est_rews,est_ws = curr_agent.EM(EM_in)
            actual_obs_diff = next_obs[agent_i] - obs[agent_i]
            actual_rews = rews[agent_i].view(-1,1)
            actual_ws = self.ws_onehot
            loss_obs = F.mse_loss(est_obs_diff, actual_obs_diff)
            loss_rew = F.mse_loss(est_rews, actual_rews)
            loss_ws = CELoss(est_ws,torch.argmax(actual_ws,dim=1))
            EM_loss = self.obs_weight * loss_obs + self.rew_weight * loss_rew + self.ws_weight * loss_ws
            EM_loss.backward()
            torch.nn.utils.clip_grad_norm_(curr_agent.policy_prime.parameters(), 1) # do we want to clip the gradients?
            curr_agent.EM_optimizer.step()

            #---------------------------------------------------------------------------------
        self.count += 1
        # ------------------------------------
        # if logger is not None:
        #     logger.add_scalars('agent%i/losses' % agent_i,
        #                        {'vf_loss': vf_loss,
        #                         'pol_loss': pol_loss},
        #                        self.niter)

            
        if self.niter % 100 == 0:
            print("Q loss",vf_loss)
            # print("Actor loss",pol_loss)
            if self.I2A:
                print("Policy Prime loss",pol_prime_loss)
                print("Environment Model loss",EM_loss)

    def inject(self,grad):
        new_grad = grad.clone()
        new_grad = self.invert(new_grad,self.params,self.param_dim)
        #print("new",new_grad[0,-8:])
        return new_grad
    
    #zerod critic
    '''# takes input gradients and activation values for params and returns scaled gradients
    def invert(self,grad,params,num_params):
        for sample in range(grad.shape[0]): # batch size
            for index in range(num_params):
                if params[sample][-1 - index] != 0:
                # last 5 are the params
                    if grad[sample][-1 - index] < 0:
                        grad[sample][-1 - index] *= ((1.0-params[sample][-1 - index])/(1-(-1))) # scale
                    else:
                        grad[sample][-1 - index] *= ((params[sample][-1 - index]-(-1.0))/(1-(-1)))
                else:
                    grad[sample][-1-index] *= 0
        for sample in range(grad.shape[0]): # batch size
            # inverts gradients of discrete actions
            for index in range(3):
                if np.abs(grad[sample][-1-num_params -index]) > 10:
                    print(grad[sample][-1-num_params  -index])
                if params[sample][-1 - num_params - index] != 0:
                # last 5 are the params
                    if grad[sample][-1 - num_params - index] < 0:
                        grad[sample][-1 - num_params - index] *= ((1.0-self.curr_pol_out[sample][-1 - num_params -index])/(1-(-1))) # scale
                    else:
                        grad[sample][-1 - num_params - index] *= ((self.curr_pol_out[sample][-1 - num_params - index]-(-1.0))/(1-(-1)))
                else:
                    grad[sample][-1 - num_params - index] *= 0
            for index in range(3):
                if params[sample][-1-num_params-index] == 0:
                    grad[sample][-1-num_params-index] *= 0
        return grad'''
    
    # non-zerod critic
    # takes input gradients and activation values for params and returns scaled gradients
    def invert(self,grad,params,num_params):
        for sample in range(grad.shape[0]): # batch size
            for index in range(num_params):
            # last 5 are the params
                if grad[sample][-1 - index] < 0:
                    grad[sample][-1 - index] *= ((1.0-params[sample][-1 - index])/(1-(-1))) # scale
                else:
                    grad[sample][-1 - index] *= ((params[sample][-1 - index]-(-1.0))/(1-(-1)))
        for sample in range(grad.shape[0]): # batch size
            # inverts gradients of discrete actions
            for index in range(3):
            # last 5 are the params
                if grad[sample][-1 - num_params - index] < 0:
                    grad[sample][-1 - num_params - index] *= ((1.0-self.curr_pol_out[sample][-1 - num_params -index])/(1-(-1))) # scale
                else:
                    grad[sample][-1 - num_params - index] *= ((self.curr_pol_out[sample][-1 - num_params - index]-(-1.0))/(1-(-1)))

        return grad
 
    def update_hard_critic(self):
        for a in self.agents:
            hard_update(a.target_critic, a.critic)

             
    def update_hard_policy(self):
        for a in self.agents:
            hard_update(a.target_policy, a.policy)
    

    def update_all_targets(self):
        """
        Update all target networks (called after normal updates have been
        performed for each agent)
        """
        for a in self.team_agents:
            soft_update(a.target_critic, a.critic, self.tau)
            soft_update(a.target_policy, a.policy, self.tau)

        for a in self.opp_agents:
            soft_update(a.target_critic, a.critic, self.tau)
            soft_update(a.target_policy, a.policy, self.tau)

        self.niter += 1

    def prep_training(self, device='gpu'):
        for a in self.team_agents:
            a.policy.train()
            a.critic.train()
            a.target_policy.train()
            a.target_critic.train()
        
        for a in self.opp_agents:
            a.policy.train()
            a.critic.train()
            a.target_policy.train()
            a.target_critic.train()

        if device == 'gpu':
            fn = lambda x: x.cuda()
        else:
            fn = lambda x: x.cpu()

        if not self.pol_dev == device:
            for a in self.team_agents:
                a.policy = fn(a.policy)
            for a in self.opp_agents:
                a.policy = fn(a.policy)
            self.pol_dev = device

        if not self.critic_dev == device:
            for a in self.team_agents:
                a.critic = fn(a.critic)
            for a in self.opp_agents:
                a.critic = fn(a.critic)
            self.critic_dev = device

        if not self.trgt_pol_dev == device:
            for a in self.team_agents:
                a.target_policy = fn(a.target_policy)
            for a in self.opp_agents:
                a.target_policy = fn(a.target_policy)
            self.trgt_pol_dev = device

        if not self.trgt_critic_dev == device:
            for a in self.team_agents:
                a.target_critic = fn(a.target_critic)
            for a in self.opp_agents:
                a.target_critic = fn(a.target_critic)
            self.trgt_critic_dev = device

    def prep_rollouts(self, device='cpu'):
        for a in self.team_agents:
            a.policy.eval()
        for a in self.opp_agents:
            a.policy.eval()

        if device == 'gpu':
            fn = lambda x: x.cuda()
        else:
            fn = lambda x: x.cpu()

        # only need main policy for rollouts
        if not self.pol_dev == device:
            for a in self.team_agents:
                a.policy = fn(a.policy)
            for a in self.opp_agents:
                a.policy = fn(a.policy)
            self.pol_dev = device

    def save(self, filename):
        """
        Save trained parameters of all agents into one file
        """
        self.prep_training(device='cpu')  # move parameters to CPU before saving
        save_dict = {'init_dict': self.init_dict,
                     'agent_params': [a.get_params() for a in self.agents]}
        torch.save(save_dict, filename)

    #Needs to be tested
    def save_actor(self, filename):
        """
        Save trained parameters of all agent's actor network into one file
        """
        self.prep_training(device='cpu')  # move parameters to CPU before saving
        save_dict = {'init_dict': self.init_dict,
                     'actor_params': [a.get_actor_params() for a in self.agents]}
        torch.save(save_dict, filename)

    #Needs to be tested
    def save_critic(self, filename):
        """
        Save trained parameters of all agent's critic networks into one file
        """
        self.prep_training(device='cpu')  # move parameters to CPU before saving
        save_dict = {'init_dict': self.init_dict,
                     'critic_params': [a.get_critic_params() for a in self.agents]}
        torch.save(save_dict, filename)

# ----------------------------
# - Pretraining Functions ----
    
    def pretrain_critic(self, sample, agent_i, parallel=False, logger=None):
        """
        Update parameters of agent model based on sample from replay buffer
        Inputs:
            sample: tuple of (observations, actions, rewards, next
                    observations, and episode end masks, cumulative discounted reward) sampled randomly from
                    the replay buffer. Each is a list with entries
                    corresponding to each agent
            agent_i (int): index of agent to update
            parallel (bool): If true, will average gradients across threads
            logger (SummaryWriter from Tensorboard-Pytorch):
                If passed in, important quantities will be logged
        """
        # rews = 1-step, cum-rews = n-step
        obs, acs, rews, next_obs, dones,MC_rews,n_step_rews,ws = sample
        curr_agent = self.agents[agent_i]
        zero_values = False
        
        # Train critic ------------------------
        curr_agent.critic_optimizer.zero_grad()
        
        if zero_values:
            all_trgt_acs = [torch.cat( # concat one-hot actions with params (that are zero'd along the indices of the non-chosen actions)
            (onehot_from_logits(pi(nobs)[:,:curr_agent.action_dim]),
             self.zero_params(pi(nobs),onehot_from_logits(pi(nobs)[:,:curr_agent.action_dim]))[:,curr_agent.action_dim:]),1)
                        for pi, nobs in zip(self.target_policies, next_obs)]    # onehot the action space but not param
            if self.TD3:
                noise = torch.randn_like(acs)*self.TD3_noise
                all_trgt_acs = [torch.cat( # concat one-hot actions with params (that are zero'd along the indices of the non-chosen actions)
            (onehot_from_logits((pi(nobs) + noise)[:,:curr_agent.action_dim]),
             self.zero_params((pi(nobs)+noise),onehot_from_logits((pi(nobs)+noise)[:,:curr_agent.action_dim]))[:,curr_agent.action_dim:]),1)
                        for pi, nobs in zip(self.target_policies, next_obs)]    # onehot the action space but not param
        else:
            if self.TD3:
                noise = torch.randn_like(acs[0]) * self.TD3_noise
                all_trgt_acs = [pi(nobs) + noise for pi, nobs in zip(self.target_policies,next_obs)]                  
            else:
                all_trgt_acs = [pi(nobs) for pi, nobs in zip(self.target_policies,next_obs)]  
            
            

        # Target critic values
        trgt_vf_in = torch.cat((*next_obs, *all_trgt_acs), dim=1)
        if self.TD3: # TODO* For D4PG case, need mask with indices of the distributions whos distr_to_q(trgtQ1) < distr_to_q(trgtQ2)
                     # and build the combination of distr choosing the minimums
            trgt_Q1,trgt_Q2 = curr_agent.target_critic(trgt_vf_in)
            if self.D4PG:
                arg = np.argmin([curr_agent.target_critic.distr_to_q(trgt_Q1).mean().data.numpy(),
                                 curr_agent.target_critic.distr_to_q(trgt_Q2).mean().data.numpy()])
                if arg: 
                    trgt_Q = trgt_Q1
                else:
                    trgt_Q = trgt_Q2
            else:
                trgt_Q = torch.min(trgt_Q1,trgt_Q2)
        else:
            trgt_Q = curr_agent.target_critic(trgt_vf_in)
        # Actual critic values
        vf_in = torch.cat((*obs, *acs), dim=1)
        if self.TD3:
            actual_value_1, actual_value_2 = curr_agent.critic(vf_in)
        else:
            actual_value = curr_agent.critic(vf_in)
        
        if self.D4PG:
                # Q1
                trgt_vf_distr = F.softmax(trgt_Q,dim=1) # critic distribution
                trgt_vf_distr_proj = distr_projection(self,trgt_vf_distr,n_step_rews[agent_i],dones[agent_i],MC_rews[agent_i],
                                                  gamma=self.gamma**self.n_steps,device='cpu') 
                if self.TD3:
                    prob_dist_1 = -F.log_softmax(actual_value_1,dim=1) * trgt_vf_distr_proj # Q1
                    prob_dist_2 = -F.log_softmax(actual_value_2,dim=1) * trgt_vf_distr_proj # Q2
                    # distribution distance function
                    vf_loss = prob_dist_1.sum(dim=1).mean() + prob_dist_2.sum(dim=1).mean() # critic loss based on distribution distance
                else:
                    prob_dist = -F.log_softmax(actual_value,dim=1) * trgt_vf_distr_proj
                    trgt_vf_distr = F.softmax(trgt_Q,dim=1) # critic distribution
                    trgt_vf_distr_proj = distr_projection(self,trgt_vf_distr,n_step_rews[agent_i],dones[agent_i],MC_rews[agent_i],
                                                      gamma=self.gamma**self.n_steps,device='cpu') 
                    # distribution distance function
                    prob_dist = -F.log_softmax(actual_value,dim=1) * trgt_vf_distr_proj
                    vf_loss = prob_dist.sum(dim=1).mean() # critic loss based on distribution distance
        else: # single critic value
            target_value = (1-self.beta)*(n_step_rews[agent_i].view(-1, 1) + (self.gamma**self.n_steps) *
                        trgt_Q * (1 - dones[agent_i].view(-1, 1))) + self.beta*(MC_rews[agent_i].view(-1,1))
            target_value.detach()
            if self.TD3: # handle double critic
                vf_loss = F.mse_loss(actual_value_1, target_value) + F.mse_loss(actual_value_2,target_value)
            else:
                vf_loss = F.mse_loss(actual_value, target_value)
        
        if self.niter % 100 == 0:
            print("Q loss",vf_loss)
        

                
            
        vf_loss.backward() 
        if parallel:
            average_gradients(curr_agent.critic)
        torch.nn.utils.clip_grad_norm_(curr_agent.critic.parameters(), 1)
        curr_agent.critic_optimizer.step()

    def update_prime(self, sample, agent_i, parallel=False, logger=None):
        obs, acs, rews, next_obs, dones,MC_rews,n_step_rews,ws = sample
        curr_agent = self.agents[agent_i]
       
        # Update policy prime
        curr_agent.policy_prime_optimizer.zero_grad()
        curr_pol_out = curr_agent.policy(obs[agent_i])
        # We take the loss between the current policy's behavior and policy prime which is estimating the current policy
        pol_prime_out = curr_agent.policy_prime(obs[agent_i]) # uses gumbel across the actions
        pol_prime_out_actions = pol_prime_out[:,:curr_agent.action_dim].float()
        pol_prime_out_params = pol_prime_out[:,curr_agent.action_dim:]
        pol_out_actions = curr_pol_out[:,:curr_agent.action_dim].float()
        pol_out_params = curr_pol_out[:,curr_agent.action_dim:]
        target_classes = torch.argmax(pol_out_actions,dim=1) # categorical integer for predicted class
        MSE =np.sum([F.mse_loss(prime[self.discrete_param_indices(target_class)],current[self.discrete_param_indices(target_class)]) for prime,current,target_class in zip(pol_prime_out_params,pol_out_params, target_classes)])
        #pol_loss = MSE + CELoss(pol_out_actions,target_classes)
        pol_prime_loss = MSE + F.mse_loss(pol_prime_out_actions,pol_out_actions)
        pol_prime_loss.backward()
        if parallel:
            average_gradients(curr_agent.policy_prime)
        torch.nn.utils.clip_grad_norm_(curr_agent.policy_prime.parameters(), 1) # do we want to clip the gradients?
        curr_agent.policy_prime_optimizer.step()

        if self.niter % 100 == 0:
            print("Policy Prime Loss",pol_prime_loss)
        self.niter += 1
        
   
    def pretrain_prime(self, sample, agent_i, parallel=False, logger=None):
        obs, acs, rews, next_obs, dones,MC_rews,n_step_rews,ws = sample
        curr_agent = self.agents[agent_i]
        zero_values = False
        if self.discrete_action:
            # Forward pass as if onehot (hard=True) but backprop through a differentiable
            # Gumbel-Softmax sample. The MADDPG paper uses the Gumbel-Softmax trick to backprop
            # through discrete categorical samples, but I'm not sure if that is
            # correct since it removes the assumption of a deterministic policy for
            # DDPG. Regardless, discrete policies don't seem to learn properly without it.
            curr_pol_out = curr_agent.policy(obs[agent_i])
            curr_pol_vf_in = gumbel_softmax(curr_pol_out, hard=True)
        else:
            curr_pol_out = curr_agent.policy_prime(obs[agent_i]) # uses gumbel across the actions

            self.curr_pol_out = curr_pol_out.clone() # for inverting action space

            # concat one-hot actions with params zero'd along indices non-chosen actions
            if zero_values:
                curr_pol_vf_in = torch.cat((gumbel, 
                                      self.zero_params(curr_pol_out,gumbel)[:,curr_agent.action_dim:]),1)
            else:
                curr_pol_vf_in = curr_pol_out

        
        all_pol_acs = []
        all_pol_acs.append(curr_pol_vf_in)
            

        vf_in = torch.cat((*obs, *all_pol_acs), dim=1)
        # invert gradient --------------------------------------
        self.params = vf_in.data
        self.param_dim = curr_agent.param_dim
        hook = vf_in.register_hook(self.inject)

        curr_agent.policy_prime_optimizer.zero_grad()
        
        pol_out_actions = curr_pol_out[:,:curr_agent.action_dim].float()
        actual_out_actions = Variable(torch.stack(acs)[agent_i],requires_grad=True).float()[:,:curr_agent.action_dim]
        pol_out_params = curr_pol_out[:,curr_agent.action_dim:]
        actual_out_params = Variable(torch.stack(acs)[agent_i],requires_grad=True)[:,curr_agent.action_dim:]

        target_classes = torch.argmax(actual_out_actions,dim=1) # categorical integer for predicted class

        MSE =np.sum([F.mse_loss(estimation[self.discrete_param_indices(target_class)],actual[self.discrete_param_indices(target_class)]) for estimation,actual,target_class in zip(pol_out_params,actual_out_params, target_classes)])

        #pol_prime_loss = MSE + CELoss(pol_out_actions,target_classes)
        pol_prime_loss = MSE + F.mse_loss(pol_out_actions,actual_out_actions)
        #pol_loss += (curr_pol_out[:curr_agent.action_dim]**2).mean() * 1e-2 # regularize size of action
        pol_prime_loss.backward()
        if parallel:
            average_gradients(curr_agent.policy_prime)
        torch.nn.utils.clip_grad_norm_(curr_agent.policy_prime.parameters(), 1) # do we want to clip the gradients?
        curr_agent.policy_prime_optimizer.step()
        hook.remove()

        if self.niter % 100 == 0:
            print("Policy Prime Loss",pol_prime_loss)
        self.niter += 1
        
   
        
    def update_EM(self, sample, agent_i, parallel=False, logger=None):
        """
        Update parameters of Environment Model based on sample from replay buffer
        Inputs:
            sample: tuple of (observations, actions, rewards, next
                    observations, and episode end masks, cumulative discounted reward) sampled randomly from
                    the replay buffer. Each is a list with entries
                    corresponding to each agent
            agent_i (int): index of agent to update
            parallel (bool): If true, will average gradients across threads
            logger (SummaryWriter from Tensorboard-Pytorch):
                If passed in, important quantities will be logged
        """
        obs, acs, rews, next_obs, dones,MC_rews,n_step_rews,ws = sample
        curr_agent = self.agents[agent_i]
       
        # Train Environment Model -----------------------------------------------------            
        curr_agent.EM_optimizer.zero_grad()

        labels = ws[0].long().view(-1,1) % self.world_status_dim # categorical labels for OH
        self.ws_onehot.zero_() # reset OH tensor
        self.ws_onehot.scatter_(1,labels,1) # fill with OH encoding
        EM_in = torch.cat((*obs, *acs),dim=1)
        est_obs_diff,est_rews,est_ws = curr_agent.EM(EM_in)
        actual_obs_diff = next_obs[agent_i] - obs[agent_i]
        actual_rews = rews[agent_i].view(-1,1)
        actual_ws = self.ws_onehot
        loss_obs = F.mse_loss(est_obs_diff, actual_obs_diff)
        loss_rew = F.mse_loss(est_rews, actual_rews)
        loss_ws = CELoss(est_ws,torch.argmax(actual_ws,dim=1))
        EM_loss = self.obs_weight * loss_obs + self.rew_weight * loss_rew + self.ws_weight * loss_ws
        EM_loss.backward()
        torch.nn.utils.clip_grad_norm_(curr_agent.policy_prime.parameters(), 1) # do we want to clip the gradients?
        curr_agent.EM_optimizer.step()

        if self.niter % 100 == 0:
            print("EM Loss",EM_loss,"Obs Loss",loss_obs,"Rew Loss:",loss_rew,"WS Loss:",loss_ws)
        self.niter += 1
        
        
    def pretrain_actor(self, sample, agent_i, parallel=False, logger=None):
        """
        Update parameters of actor based on sample from replay buffer for policy imitation (fits policy to observed actions)
        Inputs:
            sample: tuple of (observations, actions, rewards, next
                    observations, and episode end masks, cumulative discounted reward) sampled randomly from
                    the replay buffer. Each is a list with entries
                    corresponding to each agent
            agent_i (int): index of agent to update
            parallel (bool): If true, will average gradients across threads
            logger (SummaryWriter from Tensorboard-Pytorch):
                If passed in, important quantities will be logged
        """
        # rews = 1-step, cum-rews = n-step
        obs, acs, rews, next_obs, dones,MC_rews,n_step_rews,ws = sample
        curr_agent = self.agents[agent_i]
        zero_values = False
        
        
        curr_agent.policy_optimizer.zero_grad()
        
        # Train actor -----------------------
        if self.discrete_action:
            # Forward pass as if onehot (hard=True) but backprop through a differentiable
            # Gumbel-Softmax sample. The MADDPG paper uses the Gumbel-Softmax trick to backprop
            # through discrete categorical samples, but I'm not sure if that is
            # correct since it removes the assumption of a deterministic policy for
            # DDPG. Regardless, discrete policies don't seem to learn properly without it.
            curr_pol_out = curr_agent.policy(obs[agent_i])
            curr_pol_vf_in = gumbel_softmax(curr_pol_out, hard=True)
        else:
            curr_pol_out = curr_agent.policy(obs[agent_i]) # uses gumbel across the actions

            self.curr_pol_out = curr_pol_out.clone() # for inverting action space
            #gumbel = gumbel_softmax(torch.softmax(curr_pol_out[:,:curr_agent.action_dim].clone()),hard=True)
            #log_pol_out = curr_pol_out[:,:curr_agent.action_dim].clone()

            #gumbel = gumbel_softmax((curr_pol_out[:,:curr_agent.action_dim].clone()),hard=True)

            #log_pol_out = torch.log(curr_pol_out[:,:curr_agent.action_dim].clone())
            #gumbel = gumbel_softmax(log_pol_out,hard=True)
            #gumbel = onehot_from_logits(log_pol_out,eps=0.0)


            # concat one-hot actions with params zero'd along indices non-chosen actions
            if zero_values:
                curr_pol_vf_in = torch.cat((gumbel, 
                                      self.zero_params(curr_pol_out,gumbel)[:,curr_agent.action_dim:]),1)
            else:
                curr_pol_vf_in = curr_pol_out

            #print(curr_pol_vf_in)
        all_pol_acs = []
        for i, pi, ob in zip(range(self.nagents), self.policies, obs):
            if i == agent_i:
                all_pol_acs.append(curr_pol_vf_in)
            elif self.discrete_action:
                all_pol_acs.append(onehot_from_logits(pi(ob)))
            else: # shariq does not gumbel this, we don't want to sample noise from other agents actions?
                a = pi(ob)
                g = onehot_from_logits(torch.log(a[:,:curr_agent.action_dim]),hard=True)
                c = torch.cat((g,self.zero_params(a,g)[:,curr_agent.action_dim:]),1)
                all_pol_acs.append(c) # 

        vf_in = torch.cat((*obs, *all_pol_acs), dim=1)
        # invert gradient --------------------------------------
        self.params = vf_in.data
        self.param_dim = curr_agent.param_dim
        hook = vf_in.register_hook(self.inject)

        pol_out_actions = curr_pol_out[:,:curr_agent.action_dim].float()
        actual_out_actions = Variable(torch.stack(acs)[agent_i],requires_grad=True).float()[:,:curr_agent.action_dim]
        pol_out_params = curr_pol_out[:,curr_agent.action_dim:]
        actual_out_params = Variable(torch.stack(acs)[agent_i],requires_grad=True)[:,curr_agent.action_dim:]

        target_classes = torch.argmax(actual_out_actions,dim=1) # categorical integer for predicted class

        MSE =np.sum([F.mse_loss(estimation[self.discrete_param_indices(target_class)],actual[self.discrete_param_indices(target_class)]) for estimation,actual,target_class in zip(pol_out_params,actual_out_params, target_classes)])

        #pol_loss = MSE + CELoss(pol_out_actions,target_classes)
        pol_loss = MSE + F.mse_loss(pol_out_actions,actual_out_actions)
    # testing imitation
#pol_loss += (curr_pol_out[:curr_agent.action_dim]**2).mean() * 1e-2 # regularize size of action
        pol_loss.backward()
        if parallel:
            average_gradients(curr_agent.policy)
        torch.nn.utils.clip_grad_norm_(curr_agent.policy.parameters(), 1) # do we want to clip the gradients?
        curr_agent.policy_optimizer.step()
        hook.remove()

        if self.niter % 100 == 0:
            print("Actor loss",pol_loss)
        self.niter += 1
        
       

    @classmethod
    def init_from_env(cls, env, agent_alg="MADDPG", adversary_alg="MADDPG",
                      gamma=0.95, batch_size=0, tau=0.01, a_lr=0.01, c_lr=0.01, hidden_dim=64,discrete_action=True,
                      vmax = 10,vmin = -10, N_ATOMS = 51, n_steps = 5, DELTA_Z = 20.0/50,D4PG=False,beta=0,
                      TD3=False,TD3_noise = 0.2,TD3_delay_steps=2,
                      I2A = False,EM_lr=0.001,obs_weight=10.0,rew_weight=1.0,ws_weight=1.0,rollout_steps = 5,LSTM_hidden=64):
        """
        Instantiate instance of this class from multi-agent environment
        """
        team_agent_init_params = []
        
        team_alg_types = [ agent_alg for
                     atype in range(env.num_TA)]
        for acsp, obsp, algtype in zip([env.action_list for i in range(env.num_TA)], env.team_obs, team_alg_types):
            
            # changed acsp to be action_list for each agent 
                # giving dimension num_TA x action_list so they may zip properly    

            num_in_pol = obsp.shape[0]
        
            num_out_pol =  len(env.action_list)
            # num_in_EM = num_out_pol * env.num_TA + num_in_pol
            
    
            # if cont
            if not discrete_action:
                num_out_pol = len(env.action_list) + len(env.team_action_params[0])
                
                
            # obs space and action space are concatenated before sending to
            # critic network
            num_in_critic = (num_in_pol + num_out_pol) *env.num_TA
            
            team_agent_init_params.append({'num_in_pol': num_in_pol,
                                      'num_out_pol': num_out_pol,
                                      'num_in_critic': num_in_critic})

        """
        Instantiate instance of this class from multi-agent environment for the 'opp' type agents
        """
        opp_agent_init_params = []
        
        opp_alg_types = [ adversary_alg for atype in range(env.num_OA)]
        for acsp, obsp, algtype in zip([env.action_list for i in range(env.num_OA)], env.opp_team_obs, opp_alg_types):
            
            num_in_pol = obsp.shape[0]

            num_out_pol =  len(env.action_list)
            
    
            # if cont
            if not discrete_action:
                num_out_pol = len(env.action_list) + len(env.opp_action_params[0])
                
                
            # obs space and action space are concatenated before sending to
            # critic network
            num_in_critic = (num_in_pol + num_out_pol) *env.num_OA
            
            opp_agent_init_params.append({'num_in_pol': num_in_pol,
                                      'num_out_pol': num_out_pol,
                                      'num_in_critic': num_in_critic})

        ## change for continuous
        init_dict = {'gamma': gamma, 'batch_size': batch_size,
                     'tau': tau, 'a_lr': a_lr,
                     'c_lr':c_lr,
                     'hidden_dim': hidden_dim,
                     'team_alg_types': team_alg_types,
                     'opp_alg_types': opp_alg_types,
                     'team_agent_init_params': team_agent_init_params,
                     'opp_agent_init_params': opp_agent_init_params,
                     'discrete_action': discrete_action,
                     'vmax': vmax,
                     'vmin': vmin,
                     'N_ATOMS': N_ATOMS,
                     'n_steps': n_steps,
                     'DELTA_Z': DELTA_Z,
                     'D4PG': D4PG,
                     'beta': beta,
                     'TD3': TD3,
                     'TD3_noise': TD3_noise,
                     'TD3_delay_steps': TD3_delay_steps,
                     'I2A': I2A,
                     'EM_lr': EM_lr,
                     'obs_weight': obs_weight,
                     'rew_weight': rew_weight,
                     'ws_weight': ws_weight,
                     'rollout_steps': rollout_steps,
                     'LSTM_hidden': LSTM_hidden}
        instance = cls(**init_dict)
        instance.init_dict = init_dict
        return instance

    @classmethod
    def init_from_save(cls, filename):
        """
        Instantiate instance of this class from file created by 'save' method
        """
        save_dict = torch.load(filename)
        instance = cls(**save_dict['init_dict'])
        instance.init_dict = save_dict['init_dict']
        for a, params in zip(instance.agents, save_dict['agent_params']):
            a.load_params(params)
        return instance
    