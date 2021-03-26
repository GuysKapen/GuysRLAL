import random

import gym
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras import layers as nn

IMAGE_SIZE = 64
LATENT_VECTOR_SIZE = 100
DISCR_FILTERS = 64
GENER_FILTERS = 64
BATCH_SIZE = 16

# dimension input image will be rescaled

LEARNING_RATE = 0.0001
REPORT_EVERY_ITER = 100
SAVE_IMAGE_EVERY_ITER = 1000


class InputWrapper(gym.ObservationWrapper):
    def __init__(self, *args):
        super(InputWrapper, self).__init__(*args)
        old_space = self.observation_space
        self.observation_space = gym.spaces.Box(self.observation(old_space.low), self.observation(old_space.high),
                                                dtype=np.float32)

    def observation(self, observation):
        # resize to image shape
        new_obs = cv2.resize(observation, (IMAGE_SIZE, IMAGE_SIZE))
        # reshape (210, 160, 3) -> (3, 210, 160) for CNN
        new_obs = tf.transpose(new_obs, [2, 0, 1])
        return tf.cast(new_obs, dtype=np.float32) / 255.0


class Discriminator(tf.keras.models.Model):
    def get_config(self):
        pass

    def __init__(self, input_shape):
        super(Discriminator, self).__init__()

        self.conv_pipe = tf.keras.Sequential(
            (
                nn.Conv2D(filters=input_shape[0], kernel_size=4, strides=2, padding=1),
                nn.ReLU(),
                nn.Conv2D(filters=DISCR_FILTERS, kernel_size=4, strides=2, padding=1),
                nn.ReLU(),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2D(filters=DISCR_FILTERS * 2, kernel_size=4, strides=2, padding=1),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2D(filters=DISCR_FILTERS * 4, kernel_size=4, strides=2, padding=1),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2D(filters=DISCR_FILTERS * 8, kernel_size=4, strides=1, padding=0),
                nn.Activation(activation="sigmoid")
            )
        )

    def call(self, inputs, training=None, mask=None):
        conv_out = self.conv_pipe(inputs)
        return tf.squeeze(tf.reshape(conv_out, shape=(-1, 1)), axis=1)


class Generator(tf.keras.models.Model):
    def __init__(self, output_shape):
        super(Generator, self).__init__()
        self.deconv_pipe = tf.keras.Sequential(
            (
                nn.Conv2DTranspose(filters=LATENT_VECTOR_SIZE, kernel_size=4, strides=1, padding=0),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2DTranspose(filters=GENER_FILTERS * 8, kernel_size=4, strides=2, padding=1),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2DTranspose(filters=GENER_FILTERS * 4, kernel_size=4, strides=2, padding=1),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2DTranspose(filters=GENER_FILTERS * 2, kernel_size=4, strides=2, padding=1),
                nn.BatchNormalization(),
                nn.ReLU(),
                nn.Conv2DTranspose(filters=GENER_FILTERS, kernel_size=4, strides=2, padding=1),
                nn.Activation(activation='tanh')
            )
        )

    def call(self, inputs, training=None, mask=None):
        return self.deconv_pipe(inputs)

    def get_config(self):
        pass


def iterate_batches(envs, batch_size=BATCH_SIZE):
    batch = [e.reset() for e in envs]
    env_gen = iter(lambda: random.choice(envs), None)

    while True:
        e = next(env_gen)
        obs, reward, done, _ = e.step(e.action_space.sample())
        if np.mean(obs) > 0.01:
            batch.append(obs)
        if len(batch) == batch_size:
            batch_np = np.array(batch, dtype=np.float32) * 2.0 / 255.0 - 1.0
            yield tf.convert_to_tensor(batch_np)
            batch.clear()
        if done:
            e.reset()


if __name__ == '__main__':
    envs = [InputWrapper(gym.make(name)) for name in ('Breakout-v0', 'AirRaid-v0', 'Pong-v0')]
    # input_shape = envs[0].observation_space.shape
    #
    # net_discr = Discriminator(input_shape=input_shape)
    # net_gener = Generator(output_shape=input_shape)
    #
    # objective = tf.keras.losses.BinaryCrossentropy()
    # gener_optimizer = tf.keras.optimizers.Adam(lr=LEARNING_RATE, beta_1=0.5)
    # discr_optimizer = tf.keras.optimizers.Adam(lr=LEARNING_RATE, beta_1=0.5)
    #
    # log_dir = "logs/gan"
    # summary = tf.summary.create_file_writer(logdir=log_dir)
    #
    # gener_losses = []
    # discr_losses = []
    # iter_no = 0
    #
    # true_labels_v = tf.ones(BATCH_SIZE, dtype=tf.float32)
    # fake_labels_v = tf.zeros(BATCH_SIZE, dtype=tf.float32)
    #
    # for batch_v in iterate_batches(envs):
    #     with tf.GradientTape() as discr_g:
    #         gen_input_v = tf.random.normal(shape=(BATCH_SIZE, LATENT_VECTOR_SIZE, 1, 1), dtype=tf.float32)
    #         gen_output_v = net_gener(gen_input_v)
    #
    #         discr_output_true_v = net_discr(batch_v)
    #         discr_output_fake_v = net_discr(gen_output_v)
    #         discr_loss = objective(true_labels_v, discr_output_true_v) + objective(fake_labels_v, discr_output_fake_v)
    #
    #     discr_gradients = discr_g.gradient(discr_loss, net_discr.trainable_variables)
    #     discr_optimizer.apply_gradients(zip(discr_gradients, net_discr.trainable_variables))
    #
    #     discr_losses.append(discr_loss)
    #
    #     with tf.GradientTape() as gener_g:
    #         discr_output_v = net_discr(gen_output_v)
    #         gen_loss_v = objective(true_labels_v, discr_output_v)
    #
    #     gener_gradients = gener_g.gradient(gen_loss_v, net_gener.trainable_variables)
    #     gener_optimizer.apply_gradients(zip(gener_gradients, net_gener.trainable_variables))
    #
    #     gener_losses.append(gen_loss_v)
    #
    #
    #
    #