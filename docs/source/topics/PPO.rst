==================================
PPO (Proximal Policy Optimization)
==================================

The PPO algorithm is a Policy Gradient method that seeks to improve on the A2C
algorithm by implementing a surrogate objective function and loss clipping to
prevent the policy updates from moving too far in any direction away from the
previous policy. PPO first takes the ratio of the policy output for an action
taken a time t(the ratio of the probabilities of taking that action) from the
current policy over the old policy. It multiplies this by a an advantage function,
which is just a function of the actual state values and the approximated state
values. The full loss function then takes the minimum of this value and 1 +-
a clipped value multiplied by the above surrogate objective function. This 
clipping merely keeps the updated policy within a given distance from the previous 
policy. This implementation adds stability and decreases variance to the policy gradient
method. It currently is one of the best performing Reinforcement Learning
algorithms on a wide variety of applications due to its ability to do well
environments with continuous action spaces.

.. rubric:: PPO Learner

The learner controls the flow of the PPO process. It initializes the algorithm object,
as well as creates the new learning agent. The PPO learner runs the policy
through the environment for a predetermined amount of episodes and stores the
episodes on a buffer. These episodes are then passed to the
`PPO Algorithm <https://github.com/nflux/Control-Tasks/blob/docs-redo/shiva/shiva/algorithms/PPOAlgorithm.py>`_
which will update a new policy using these episodes and the objective function
described above. It will iterate through this process for a configured episode count.

.. rubric:: PPO Algorithm

The `PPO Algorithm <https://github.com/nflux/Control-Tasks/blob/docs-redo/shiva/shiva/algorithms/PPOAlgorithm.py>`_
is an `Algorithm <https://github.com/nflux/Control-Tasks/blob/docs-redo/shiva/shiva/algorithms/Algorithm.py>`_
that controls the updating of the PPO policy. It calculates the probabilities
for the ratio variable, as well as calculates entropy. Our implementation
includes an Entropy Loss that helps stabilization, as well as increases exploration
by ensuring that the policy is not too sure of a given action.

.. rubric:: Imitation Agent

The `Imitation Agent <https://github.com/nflux/Control-Tasks/blob/docs-redo/shiva/shiva/agents/ImitationAgent.py>`_
is an `Agent <https://github.com/nflux/Control-Tasks/blob/docs-redo/shiva/shiva/agents/ImitationAgent.py>`_
that contains the policy network that we are wanting to train, and is used
throughout the learning process. 
