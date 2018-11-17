import re
import os
import torch
import torch.nn.functional as F
import torch.distributed as dist
from torch.autograd import Variable
import numpy as np

def e_greedy(logits, eps=0.0):
    """
    Given batch of logits, return one-hot sample using epsilon greedy strategy
    (based on given epsilon)
    
    ** Modified to return True if random action is taken, else return False
    """
    # get best (according to current policy) actions in one-hot form
    argmax_acs = (logits == logits.max(1, keepdim=True)[0]).float()
    if eps == 0.0:
        return argmax_acs,False
    # get random actions in one-hot form
    rand_acs = Variable(torch.eye(logits.shape[1])[[np.random.choice(
        range(logits.shape[1]), size=logits.shape[0])]], requires_grad=False)
    # chooses between best and random actions using epsilon greedy
    explore = False
    rand = torch.rand(logits.shape[0])
    for i,r in enumerate(rand):
        if r < eps:
            explore = True        
    return torch.stack([argmax_acs[i] if r > eps else rand_acs[i] for i, r in
                        enumerate(rand)]) , explore
def pretrain_process(fname,pt_episodes,episode_length,num_features):
    with open(fname) as f:
        content = f.readlines()

    content = [x.strip() for x in content]
    pt_obs = []
    pt_status = []
    pt_actions = []
    garbage = True
    skip_counter = 0
    Tackle = False
    print("Loading pretrain data")
    for c in content[:episode_length*pt_episodes*3]:
        if c.split(' ')[3] != 'StateFeatures' and garbage:
            next
        else:
            garbage = False
        if not garbage and skip_counter < 2:
            skip_counter +=1
            next
        if not garbage:
            if c.split(' ' )[3] == 'StateFeatures':
                ob = []
                for j in range(num_features):
                    ob.append(float(c.split(' ')[4+j]))
            elif 'agent' in c.split(' ')[3]:
                action_string = c.split(' ')[4]
                #print(action_string)
                if "Dash"  in action_string: 
                    result = re.search('Dash((.*),*)', action_string)
                    power = float(result.group(1).split(',')[0][1:])
                    direction = float(result.group(1).split(',')[1][:-1])
                    #a = np.random.uniform(-1,1,8)
                    a = np.zeros(8)
                    a[0] = 1.0
                    a[3] = power/100.0
                    a[4] = direction/180.0
                elif "Turn"  in action_string:
                    result = re.search('Turn((.*))', action_string)
                    direction =float(result.group(1)[1:-1])
                    power = float(-1440)
                    a = np.zeros(8)
                    #a = np.random.uniform(-1,1,8)
                    a[1] = 1.0
                    a[5] = direction/180.0
                elif "Kick"  in action_string: 
                    result = re.search('Kick((.*),*)', action_string)
                    power = float(result.group(1).split(',')[0][1:])
                    direction = float(result.group(1).split(',')[1][:-1])
                    #a = np.random.uniform(-1,1,8)
                    a = np.zeros(8)
                    a[2] = 1.0
                    a[6] = (power/100.0)*2 - 1
                    a[7] = direction/180.0
                elif "Tackle"  in action_string: 
                    result = re.search('Tackle((.*),*)', action_string)
                    power = float(result.group(1).split(',')[0][1:])
                    direction = float(result.group(1).split(',')[1][:-1])
                    # Throw away entry
                    Tackle = True
            elif c.split(' ' )[3] == 'GameStatus':
                stat = float(c.split(' ' )[4])
                if not Tackle:
                    pt_actions.append([x for x in a])
                    pt_status.append(stat)
                    pt_obs.append(ob)
                else:
                    Tackle = False
    pt_obs = np.asarray(pt_obs)
    pt_status = np.asarray(pt_status)
    pt_actions = pt_actions
    return pt_obs,pt_status,pt_actions


def zero_params(num_TA,params,action_index):
    for i in range(num_TA):
        if action_index[i] == 0:
            params[i][2] = 0
            params[i][3] = 0
            params[i][4] = 0
        if action_index[i] == 1:
            params[i][0] = 0
            params[i][1] = 0
            params[i][3] = 0
            params[i][4] = 0
        if action_index[i] == 2:
            params[i][0] = 0
            params[i][1] = 0
            params[i][2] = 0
    return params


# returns the distribution projection
def distr_projection(self,next_distr_v, rewards_v, dones_mask_t, cum_rewards_v, gamma, device="cpu"):
    next_distr = next_distr_v.data.cpu().numpy()
    rewards = rewards_v.data.cpu().numpy()
    cum_rewards = cum_rewards_v.data.cpu().numpy()
    dones_mask = dones_mask_t.cpu().numpy().astype(np.bool)
    batch_size = len(rewards)
    proj_distr = np.zeros((batch_size, self.N_ATOMS), dtype=np.float32)

    for atom in range(self.N_ATOMS):
        tz_j = np.minimum(self.Vmax, np.maximum(self.Vmin, 
                                                (1-self.beta)*(rewards + (self.Vmin + atom * self.DELTA_Z) * gamma) + (self.beta)*cum_rewards))
        b_j = (tz_j - self.Vmin) / self.DELTA_Z
        l = np.floor(b_j).astype(np.int64)
        u = np.ceil(b_j).astype(np.int64)
        eq_mask = u == l
        proj_distr[eq_mask, l[eq_mask]] += next_distr[eq_mask, atom]
        ne_mask = u != l
        proj_distr[ne_mask, l[ne_mask]] += next_distr[ne_mask, atom] * (u - b_j)[ne_mask]
        proj_distr[ne_mask, u[ne_mask]] += next_distr[ne_mask, atom] * (b_j - l)[ne_mask]


    if dones_mask.any():
        proj_distr[dones_mask] = 0.0

        tz_j = np.minimum(self.Vmax, np.maximum(self.Vmin, rewards[dones_mask]))
        b_j = (tz_j - self.Vmin) / self.DELTA_Z
        l = np.floor(b_j).astype(np.int64)
        u = np.ceil(b_j).astype(np.int64)
        eq_mask = u == l
        eq_dones = dones_mask.copy()
        eq_dones[dones_mask] = eq_mask
        if eq_dones.any():
            proj_distr[eq_dones, l[eq_mask]] = 1.0
        ne_mask = u != l
        ne_dones = dones_mask.copy()
        ne_dones[dones_mask] = ne_mask
        if ne_dones.any():
            proj_distr[ne_dones, l[ne_mask]] = (u - b_j)[ne_mask]
            proj_distr[ne_dones, u[ne_mask]] = (b_j - l)[ne_mask]
    return torch.FloatTensor(proj_distr).to(device)


# https://github.com/ikostrikov/pytorch-ddpg-naf/blob/master/ddpg.py#L11
def soft_update(target, source, tau):
    """
    Perform DDPG soft update (move target params toward source based on weight
    factor tau)
    Inputs:
        target (torch.nn.Module): Net to copy parameters to
        source (torch.nn.Module): Net whose parameters to copy
        tau (float, 0 < x < 1): Weight factor for update
    """
    for target_param, param in zip(target.parameters(), source.parameters()):
        target_param.data.copy_(target_param.data * (1.0 - tau) + param.data * tau)

# https://github.com/ikostrikov/pytorch-ddpg-naf/blob/master/ddpg.py#L15
def hard_update(target, source):
    """
    Copy network parameters from source to target
    Inputs:
        target (torch.nn.Module): Net to copy parameters to
        source (torch.nn.Module): Net whose parameters to copy
    """
    for target_param, param in zip(target.parameters(), source.parameters()):
        target_param.data.copy_(param.data)

# https://github.com/seba-1511/dist_tuto.pth/blob/gh-pages/train_dist.py
def average_gradients(model):
    """ Gradient averaging. """
    size = float(dist.get_world_size())
    for param in model.parameters():
        dist.all_reduce(param.grad.data, op=dist.reduce_op.SUM, group=0)
        param.grad.data /= size

# https://github.com/seba-1511/dist_tuto.pth/blob/gh-pages/train_dist.py
def init_processes(rank, size, fn, backend='gloo'):
    """ Initialize the distributed environment. """
    os.environ['MASTER_ADDR'] = '127.0.0.1'
    os.environ['MASTER_PORT'] = '29500'
    dist.init_process_group(backend, rank=rank, world_size=size)
    fn(rank, size)

def onehot_from_logits(logits, eps=0.0):
    """
    Given batch of logits, return one-hot sample using epsilon greedy strategy
    (based on given epsilon)
    """
    # get best (according to current policy) actions in one-hot form
    argmax_acs = (logits == logits.max(1, keepdim=True)[0]).float()
    if eps == 0.0:
        return argmax_acs
    # get random actions in one-hot form
    rand_acs = Variable(torch.eye(logits.shape[1])[[np.random.choice(
        range(logits.shape[1]), size=logits.shape[0])]], requires_grad=False)
    # chooses between best and random actions using epsilon greedy
    return torch.stack([argmax_acs[i] if r > eps else rand_acs[i] for i, r in
                        enumerate(torch.rand(logits.shape[0]))])

# modified for PyTorch from https://github.com/ericjang/gumbel-softmax/blob/master/Categorical%20VAE.ipynb
def sample_gumbel(shape,eps=1e-20,tens_type=torch.FloatTensor):  
    """Sample from Gumbel(0, 1)"""
    U = Variable(tens_type(*shape).uniform_(), requires_grad=False)
    return -torch.log(-torch.log(U + eps) + eps)

# modified for PyTorch from https://github.com/ericjang/gumbel-softmax/blob/master/Categorical%20VAE.ipynb
def gumbel_softmax_sample(logits, temperature):
    """ Draw a sample from the Gumbel-Softmax distribution"""
    y = logits + sample_gumbel(logits.shape, tens_type=type(logits.data))
    return F.softmax(y / temperature, dim=1)

# modified for PyTorch from https://github.com/ericjang/gumbel-softmax/blob/master/Categorical%20VAE.ipynb
def gumbel_softmax(logits, temperature=1.0, hard=False):
    """Sample from the Gumbel-Softmax distribution and optionally discretize.
    Args:
      logits: [batch_size, n_class] unnormalized log-probs
      temperature: non-negative scalar
      hard: if True, take argmax, but differentiate w.r.t. soft sample y
    Returns:
      [batch_size, n_class] sample from the Gumbel-Softmax distribution.
      If hard=True, then the returned sample will be one-hot, otherwise it will
      be a probabilitiy distribution that sums to 1 across classes
    """
    y = gumbel_softmax_sample(logits, temperature)
    if hard:
        y_hard = onehot_from_logits(y)
        y = (y_hard - y).detach() + y
    return y
