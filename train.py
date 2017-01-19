import json, pickle, operator, re, time
import tensorflow as tf, numpy as np
from config import Config
from keras.preprocessing import sequence

def train(config = Config()):
    learning_rate = 0.001

    sess = tf.Session(config=tf.ConfigProto(log_device_placement=False))
    model = config.vqamodel(
            batch_size=config.batch_size,
            feature_dim=config.feature_dim,
            proj_dim=config.proj_dim,
            word_num=config.word_num,
            embed_dim=config.embed_dim,
            ans_candi_num=config.ans_candi_num,
            n_lstm_steps=config.n_lstm_steps)

    image_feat, question, answer, loss_op = model.trainer()
    saver = tf.train.Saver(max_to_keep = 50)

    train_op = tf.train.AdamOptimizer(learning_rate).minimize(loss_op)
    sum_writer = tf.train.SummaryWriter(config.log_path, sess.graph)
    loss_sum_op = tf.scalar_summary('train_loss', loss_op)

    sess.run(tf.initialize_all_variables())
    if config.checkpoint:
        saver.restore(sess, config.model_path+"-%d"%(checkpoint))

    from_idx = range(0, config.training_num, config.batch_size)
    to_idx = range(config.batch_size, config.training_num, config.batch_size)

    annotations_result = pickle.load(open(config.annotations_result_path, 'rb'))
    image_ids = annotations_result['image_ids']
    questions = np.array(annotations_result['questions'])
    answers = np.array(annotations_result['answers'])

    imgix2featix = pickle.load(open(config.imgix2featix, 'rb'))
    q_word2ix = pickle.load(open(config.worddic_path+'q_word2ix', 'rb'))
 
    questions = map(lambda ques :
                [q_word2ix[word] for word in ques.lower() if word in q_word2ix],
                questions)
    questions = np.array(sequence.pad_sequences(
                    questions, padding='post', maxlen=config.n_lstm_steps))
    feats = np.load(config.feats_path)
    feats = feats[[imgix2featix[imgix] for imgix in image_ids]]

    print "*** Training Start ***"
    sum_step = 0
    for epoch in range(config.max_epoch):
        print "Start running epoch %d" % (epoch)
        t = time.time()

        shuffler = np.random.permutation(config.training_num)
        feats = feats[shuffler]
        questions = questions[shuffler]
        answers = answers[shuffler]
        tot_loss = 0.0
        for (start, end) in zip(from_idx, to_idx):
            # make curr_image_feat [batch_size, feature_dim]
            curr_image_feat = feats[start:end]
            # make curr_question [batch_size, n_lstm_steps]
            curr_question = questions[start:end]
            # make curr_answer [batch_size]
            curr_answer = answers[start:end]

            _, loss, summary = sess.run([train_op, loss_op, loss_sum_op],
                    feed_dict = {image_feat : curr_image_feat,
                                question : curr_question,
                                answer : curr_answer})
            sum_writer.add_summary(summary, sum_step)
            sum_step += 1
            tot_loss += loss

        print "Total Loss : %.3f" %(tot_loss/len(to_idx))
        print "End running epoch %d : %dmin" %(epoch, (time.time()-t)/60)
        saver.save(sess, os.path.join(config.model_path, 'model'),
                global_step = epoch)


if __name__ == '__main__':
    train()


