

'''

    Shiva Testing Sandbox

'''


# basically import shiva
from MetaLearner import initialize_meta

# declare the path
ini_path = "Shiva/Initializers"

meta = initialize_meta(ini_path)

meta.learners[0].save



# then you can have an overview of all the different learners running at same time
# maybe we can make a gui or do something
# maybe we can set up tensorboard here with methods from meta


