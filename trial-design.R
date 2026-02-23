library(dplyr)
library(tidyr)
library(readr)

pair_trial_design <- expand_grid(
  bigger_is_more_dangerous = c(T,F),
  bigger_is_living = c(T,F),
  smaller_is_living = c(T,F),
  rep = 1:15
) |>
  select(-rep)

write_csv(pair_trial_design, "data/pair-trial-design.csv")

size_danger_ranks <- read_csv(
  "data/size-danger-ranks-60words.csv",
  col_select = c(1:4),
  col_types = 'icii'
)

keep_trying <- TRUE
attempt_max <- 1000
attempt_count <- 0
na_count_best <- Inf
while (keep_trying) {
  word_pairs <- attempt_valid_pair_design(pair_trial_design, size_danger_ranks)
  na_count <- sum(is.na(word_pairs))
  if (na_count < na_count_best) {
    na_count_best <- na_count
    word_pairs_best <- word_pairs
  }
  attempt_count <- attempt_count + 1
  keep_trying <- na_count > 0 && attempt_count < attempt_max
}
cat("na_count_best: ", na_count_best)

expand_grid(rep = 1:4, word = 1:60)
