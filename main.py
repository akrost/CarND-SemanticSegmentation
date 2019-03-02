#!/usr/bin/env python3
import os.path
import tensorflow as tf
import time
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    graph = tf.get_default_graph()
    model = tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)

    image_input = graph.get_tensor_by_name(vgg_input_tensor_name)
    keep_prob = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    layer3_out = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    layer4_out = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    layer7_out = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)

    return image_input, keep_prob, layer3_out, layer4_out, layer7_out
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # Conv - 7
    layer7_conv = tf.layers.conv2d(vgg_layer7_out, num_classes, kernel_size=1, padding='same', name='layer7_conv')
    # DeConv - 7
    layer7_deconv = tf.layers.conv2d_transpose(layer7_conv, num_classes, kernel_size=4, strides=(2,2), padding='same', name='layer7_deconv')
    # Conv - 4
    layer4_conv = tf.layers.conv2d(vgg_layer4_out, num_classes, kernel_size=1, padding='same', name='layer4_conv')
    # Skip - 4
    skip_4 = tf.add(layer7_deconv, layer4_conv)
    # DeConv - 4
    layer4_deconv = tf.layers.conv2d_transpose(skip_4, num_classes, kernel_size=4, strides=(2,2), padding='same', name='layer4_deconv')
    # Conv - 3
    layer3_conv = tf.layers.conv2d(vgg_layer3_out, num_classes, kernel_size=1, padding='same', name='layer3_conv')
    # Skip - 3
    skip3 = tf.add(layer4_deconv, layer3_conv)
    # DeConv - 3
    layer3_deconv = tf.layers.conv2d_transpose(skip3, num_classes, kernel_size=4, strides=(2,2), padding='same', name='layer3_deconv')

    return layer3_deconv
tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    labels = tf.reshape(correct_label, (-1, num_classes))

    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=labels)
    loss = tf.reduce_mean(cross_entropy)

    train_op = tf.train.AdamOptimizer(learning_rate).minimize(loss)
    return logits,  train_op, loss
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    print("Start training")

    for epoch in range(epochs):
        start_time = time.clock()
        batches = get_batches_fn(batch_size)

        for batch_input, batch_label in batches:
             _, loss = sess.run([train_op, cross_entropy_loss],
                                feed_dict={input_image: batch_input,
                                           correct_label: batch_label,
                                           keep_prob: 0.5,
                                           learning_rate:1e-3})
        end_time = time.clock()
        time_delta = end_time - start_time
        print("Epoch: {}/{}, Traning Time: {} seconds, Loss: {}".format(epoch, epochs, time_delta, loss))
tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)  # KITTI dataset uses 160x576 images
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    num_epochs = 10
    batch_size = 1

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # Build NN using load_vgg, layers, and optimize function
        correct_label = tf.placeholder(tf.int32)
        learning_rate = tf.placeholder(tf.float32)

        input_image, keep_prob, layer3_out, layer4_out, layer7_out = load_vgg(sess, vgg_path)
        last_layer = layers(layer3_out, layer4_out, layer7_out, num_classes)
        logits, train_op, loss = optimize(last_layer, correct_label, learning_rate, num_classes)

        # Train NN using the train_nn function
        sess.run(tf.global_variables_initializer())
        train_nn(sess, num_epochs, batch_size, get_batches_fn, train_op, loss, input_image, correct_label,
                 keep_prob, learning_rate)

        # Save inference data using helper.save_inference_samples
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)

        # OPTIONAL: Apply the trained model to a video


if __name__ == '__main__':
    run()