
--- PAGE 1 ---
Introduction to Deep Learning

--- PAGE 2 ---
Learning Outcomes
Upon completion of this session, the learners should be able to:
- describe the basic operation of artificial neural network
- describe different types of deep learning networks
- describe what is activation function, loss function and optimizer

--- PAGE 3 ---
WHAT IS ARTIFICIAL NEURAL NETWORK?

--- PAGE 4 ---
Artificial Neural Network (ANN)
- Consists of many computation unit called neurons
- Learns a complex mapping function that map any input X to any 
output Y by training with lots of data
( )

--- PAGE 5 ---
ANN and Deep Learning
- Deep learning network is just 
an ANN with many layers
- State-of-the-art models use 
hundreds of layers.
- Layers allow the deep learning 
network to learn increasingly 
complex concepts (e.g., a 
human face) out of simple 
concepts (lines, edges)

--- PAGE 6 ---
Artificial Neuron
- A neuron multiplies each input features ( 1,  2,  3,   ) by a corresponding weight 
( 1,  2,  3,   ) and then adds these values together together with a bias term  .
- This value is then put through a function called the activation function.
Activation 
function
=  (
+  )
= Activation 
Function

--- PAGE 7 ---
Neural Network with Single Hidden Layer
( 3)
( 2)
( 1)
1 11 +  2 21 +  1 =  1
21  22
1 12 +  2 22 +  2 =  2
1 13 +  2 23 +  3 =  3
2    11
23 + 
= 
This can be rewritten in matrix form:
and more concisely: 
=    + 
=  ( )
where 
is a vector of shape (1, 2)
is a matrix of shape (2, 3) 
and   is a vector of shape (3,1)
=  (
)
1 =  ( 1)
2 =  ( 2)
3 =  ( 3)

--- PAGE 8 ---
Multiple Hidden Layers
Hidden layer 1
Hidden layer 2
- Output from previous layer (hidden layer 1) 
becomes input to the current layer (hidden 
layer 2)
- The weights will be of shape (number of 
neurons in the previous layer, number of 
neurons in the current layers)
In this example: 
for hidden layer 2 is of shape (3, 4) 
for hidden layer 2 is of shape (4,1) 
for hidden layer 2 is of shape (4,1) 

--- PAGE 9 ---
Fully-Connected Neural Network (Dense Network)
- Fully-connected network contains 
multiple neurons arranged in 
layers. 
- Each neuron is connected to every 
other neurons in the immediate 
layer before and after it.
Input layer
Hidden layer 1
Hidden layer 2
Output layer

--- PAGE 10 ---
Neural Networks   Recurrent Network (RNN)
- Neurons get feedback from its own 
output. 
- Use for processing data with time or 
sequence information.
- Successfully used for machine 
translation, language modelling and 
time series prediction
Timestep 0
Timestep 1
Timestep 4
Timestep 2
Timestep 3

--- PAGE 11 ---
Neural Networks   Convolutional Neural Network
- Neurons are connected to small set of inputs only 
- Efficient for computer vision tasks such as object detection, image classification

--- PAGE 12 ---
ACTIVATION FUNCTIONS

--- PAGE 13 ---
Purpose of Activation Functions
- Firing Decision
- helps to decide if the neurons should fire or not - fire only if they are 
relevant to the prediction (mathematical gate)
- Bounded Values
- Some activation functions provide a bound to the output values. This 
provides more stability during training
- Non-linearity
- Introduce non-linearity to the network.
- Most of the interesting problems in real-life are non-linear in nature 
and that requires a non-linear neural network to handle them.

--- PAGE 14 ---
Activation Functions
- There are many different activation functions:
- Linear Function
- Sigmoid/Logistic
- Tanh (Hyperbolic Tangent)
- SoftMax
- RELU (Rectified Linear Unit)
- Leaky RELU
- SELU (Scaled Exponential Linear Unit)
- Parametric Rectified Linear Unit.
- SoftPlus
- 

--- PAGE 15 ---
Linear and Sigmoid
- Linear
  = 
- Output is proportional to the input multiplied by 
weight.
- Generally used for regression at the output layer
- Sigmoid
  ( ) =
1+
- Output values bounded between 0 and 1 
- Generally used for binary prediction at the 
output layer
Linear
g(x)
x
Sigmoid
g(x)
x

--- PAGE 16 ---
TanH and Softmax
TanH
- g( ) = tanh( )
- Default activation for RNN layer
Softmax
  ( ) =
=1
,  = ( 1,  2,   ,  ),  n = number of classes
- One output for each class.
- Value will be normalized to between 0 and 1 such that values for all 
classes summed to 1.
- This allows comparison and thus supports multi-class classification.
- Commonly used in output layer for a multi-class classifier with the 
cross-entropy loss function.
Tanh
-1
g(x)
x
softmax
Layer
0.11
0.32
0.02
Values 
added 
up to 
1.0

--- PAGE 17 ---
RELU   Rectified Linear Unit
- ReLU
  ( ) = max{0,  }
- Looks like linear function but is non-linear.
- It is the default activation function (hidden layer) for 
many neural networks
ReLU
x
g(x)
Y = x

--- PAGE 18 ---
Which Activation Function to use?
- Output layer
- Activation function is chosen based on the output type:
- Regression problem: use linear activation function. 
- Binary Classification: use sigmoid for the single output neuron in the 
output layer
- Multiclass Classification: use softmax activation function, one output 
neuron per class 
- Hidden layer
- Common to start with  ReLU  activation function and use others to improve 
performance
- Input layer
- No activation function

--- PAGE 19 ---
LOSS FUNCTIONS   OPTIMIZERS

--- PAGE 20 ---
How does Neural Network Learn? 
Actual 
output 
value
Ground 
truth 
value 
forward pass
backpropagate error and adjust weights 
to minimize errors (optimization)
input
calculate the error 
using loss function

--- PAGE 21 ---
Back Propagation
- Back propagation is a highly efficient algorithm that derives the 
optimal weight values in all the layers.
- It uses gradient descent and the chain rules to determine how to 
adjust the weights in each neuron in the network. 
- The weight adjustments start from the output layer (where the 
error is calculated) and work back towards the input layer

--- PAGE 22 ---
Loss Functions
- Loss function
- measures how much difference between correct (ground truth) output and 
predicted output
- A loss function should return a high value for bad prediction and low value 
for good prediction

--- PAGE 23 ---
Common types of Loss Functions
- We can use different loss functions for different problems. 
- Here are the list of loss functions for most common, well-known problems:
Problem Type
Loss Function
Binary Classification
Binary Cross-entropy
Multi-class Classification
Categorical Cross-entropy
Regression
Mean-Squared Error

--- PAGE 24 ---
Cross Entropy Loss Function
- Also called Log loss function.
- Depending on how you encode your target label, you will use either 
categorical_crossentropy or 
sparse_categorical_crossentropy in Keras
- Assuming we have 3 different classes: 0, 1, 2, and assume our 
target labels for two samples are [1, 2], we have two ways of 
representing the target labels:
- One-hot-encoded target labels: y_true = [[0,1,0],[0,0,1]]
- Integer target labels: y_true = [1,2]

--- PAGE 25 ---
Categorical Cross Entropy
y_true = [1, 2]
y_pred = [[0.05, 0.95, 0], [0.1, 0.8, 0.1]]
loss = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred)
assert loss.shape == (2,)
print(loss.numpy())
Output: array([0.0513, 2.303], dtype=float32)
y_true = [[0, 1, 0], [0, 0, 1]]
y_pred = [[0.05, 0.95, 0], [0.1, 0.8, 0.1]]
loss = tf.keras.losses.categorical_crossentropy(y_true, y_pred)
assert loss.shape == (2,)
print(loss.numpy())
Output: array([0.0513, 2.303], dtype=float32)
target is integer
target is one hot-
encoded

--- PAGE 26 ---
Regression Loss Function
- For regression problem where the output is a single continuous 
value, we can use the Mean-Squared Error loss function:
=1
( )2
Where 
= predicted value for sample 
= ground truth for sample 
= total number of samples
- The output layer will be a single unit (for single output prediction)

--- PAGE 27 ---
Optimizer
- Optimizer adjust the weights based 
on the errors in the prediction (as 
measured by loss function), using 
gradient descent
- Different optimizers have different 
ways to achieve the gradient descent
The 2D plane represents the cost function 
parametrized by weights  1 and  2
3  4

--- PAGE 28 ---
Training Epochs and Training Steps
- When training a neural network, we usually feed the network with a batch of 
samples, instead of a single sample at a time.
- Training Epoch refers to one iteration (forward pass + backward pass) over ALL
training samples.
- Training Step refers to one iteration (forward + backward pass) over a single 
batch of samples. Each training step involves a gradient update of weights
- Example: 
- Total number of samples = 1000
- Batch size = 10
- 1 training step involves 10 samples
- 1 epoch consists of 100 training steps

--- PAGE 29 ---
Learning Rate 
- Learning rate determines how fast the weights are adjusted by optimizer during 
gradient descent
- Too high a learning rate  will cause the model to not converge (overshoots the 
minimum point of loss function)
- Too slow a learning rate will cause the model to converge too slowly 
- Learning rate can be fixed or varies throughout the training epochs

--- PAGE 30 ---
Controlling Deep Learning Capacity
When setting up a neural network, we are confronted with 
the questions about depth (how many layers of neurons) 
and the width (how many neurons in each layer).
- The number of units in a layer is referred to as the 
width.
- The number of layer is referred to as the depth.
The depth and width affect the capacity of the network.
Incorrect capacity can lead to over- or underfitting.
There are no rules to determine the best depth or width of a 
ANN for a particular problem
- Determine through experimentation
Layer 2
Layer 3
Layer 1
(input)
Layer 4
(Output)
Sequential Model 
Depth
Width

--- PAGE 31 ---
Capacity of Neural Network
- As we vary our depth and width, we 
should monitor the training process.
- In the example on the right, we see 
that although the accuracy 
calculated based on the training set 
increases, the same model accuracy 
decreases for the validation set 
- this is a sure sign of overfitting.
- We can either decrease the 
width/depth or employ 
regularization methods such as L1/L2 
regularization or drop-out.