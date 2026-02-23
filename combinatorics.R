library(tidyr)
library(ggplot2)
library(dplyr)

# **Considering combinatorics**
#
#   I’m working through a combinatorics problem. I have v words, each appearing in 4 pairs, and I want the total trials to be around 120. Each trial is a pair, so the block size is 2. This is similar to a BIBD. I’m calculating that v should be around 60 to make b = 120 work. I also need to ensure that the graph is simple, 4-regular, and that all pairs are unique. So, the answer seems to be 60 unique words.
# You’re basically designing a balanced pairing scheme, which is the same as a regular graph problem.
#
# Let:
#
#   - v = number of unique words
#   - r = number of times each word appears (its “degree”)
#   - b = number of trials (each trial is one pair of words)
#
# Each trial uses 2 words, so the total number of word-occurrences is both:
#
#   - vr (each of the `v` words appears `r` times), and
#   - 2b (each of the `b` trials has 2 words).
#
# So:
#   2b == 4v
#
# With `r = 4`:
#
#     2b == 4v, b == 2v
#
# You want about `120` trials. To hit 120 exactly:
#
#     2v == 120, v == 60
#

balanced_word_pair_trials <- function(r, b) {
  b / (r / 2)
}

x <- tibble(
  num_repeats = 1:8,
  num_trials = 120,
  num_unique_words = balanced_word_pair_trials(r = num_repeats, b = num_trials)
)

ggplot(x, aes(x = num_repeats, y = num_unique_words)) +
  geom_point() +
  xlab("number of repeats per word") +
  ylab("number of unique words") +
  ggtitle("For 120 trials ...") +
  theme_classic()
