# Networks

## Overview

To enable experimentation, the networks architecture are as flexible as the config file permits. The agent implementation will create the specific network class type with the characteristics given by the config, such as the below example for an actor/critic algorithm

```python
[Network]
actor = {'layers': [1024, 512, 256, 128], 'activation_function': ['ReLU', 'ReLU','ReLU', 'ReLU'], 'output_function': None, 'last_layer': True, 'gumbel': True}
critic = {'layers': [1024, 512, 256, 128], 'activation_function': ['ReLU', 'ReLU','ReLU', 'ReLU'], 'output_function': None, 'last_layer': True}
```

The network constructor requires the following attributes in the Network section of the config file
    * layers            list type whose elements will indicate the layer size
    * activation_function        list indicating the torch activation function name used on each layer
    * output_function        optional torch activation function, default None
    * last_layer            if last layer should be included, default True
    * gumbel            only if SoftMaxHeadDynamicLinearNetwork class is used, default False


## [DynamicLinearNetwork class](../shiva/networks/DynamicLinearNetwork.py)

We currently have two available types of constructors who dynamically build the network using PyTorch framework. These are:
* DynamicLinearSequential: creates a [torch.nn.Sequential](https://pytorch.org/docs/stable/nn.html#sequential) with [linear transformations](https://pytorch.org/docs/stable/nn.html#linear) on the incoming data
* SoftMaxHeadDynamicLinearNetwork: similar to DynamicsLinearSequential but with the extension of handling a discrete and parameterized action space with choice of a softmaxed or gumbel output
