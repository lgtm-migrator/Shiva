# Using Shiva with Unity

We are using the [Python API UnityEnvironment](https://github.com/Unity-Technologies/ml-agents) provided by Unity. To run on Shiva, all you need is the binary file for the scene you want to load for your environment. Here are some requirements with regards the build, and where/how to use the API.

For additional documentation, [Unity API](https://github.com/Unity-Technologies/ml-agents/blob/master/docs/Python-API.md) is available if wanting to extend new features.

**Building Scenes on Unity Editor**
* Recommended settings for the player under **Player Settings > :**
  - Run in background: True
  - Display Resolution Dialog: Disabled
* For the Prefabs/Agents
  - Make sure the **Behaviour Parameters** has no loaded model and it's empty
  - Stacked observations are supported
  - Only one brain is supported (for now)
  - Actions should come in one single branch, either continuous or discrete (no parametrized)
* The file for the **Scene_name.x86_64** extension should be placed in the **shiva/envs/unitybuilds/** and declared in the **exec** attribute for the config.

**Config Templates**
  - The attribute setted in the config will be accessible as a class attribute for the [UnityWrapperEnvironment class](../shiva/envs/UnityWrapperEnvironment.py).
Here's the template

```
[Environment]
type='UnityWrapperEnvironment'
exec='shiva/envs/unitybuilds/Scene_name/Scene_name.x86_64'
env_name='Scene_name'
train_mode = True
```

* Note that the **env_name** attribute must be the Brain name on Unity.
