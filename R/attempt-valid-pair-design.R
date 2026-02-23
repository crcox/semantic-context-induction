attempt_valid_pair_design <- function(pair_trial_design, size_dang_ranks) {
  size_dang_ranks <- size_dang_ranks |> mutate(rep_count = 0)
  ntrials <- nrow(pair_trial_design)
  word_pairs <- matrix(nrow = 2, ncol = ntrials, dimnames = list(type = c("bigger", "smaller"), pair = NULL))

  for (i in seq_len(ntrials)) {
    x <- pair_trial_design[i, ] |> as.list()
    smaller_domain <- if (x$smaller_is_living) "living" else "nonliving"
    bigger_domain <- if (x$bigger_is_living) "living" else "nonliving"
    bigger_word_pool <- size_dang_ranks |>
      filter(rep_count < 4) |>
      filter(
        size_rank > min(size_rank[domain == smaller_domain]),
      ) %>%
      {
        if (x$bigger_is_more_dangerous) {
          filter(., danger_rank > min(danger_rank[domain == smaller_domain]))
        } else {
          filter(., danger_rank < max(danger_rank[domain == smaller_domain]))
        }
      } |>
      filter(
        domain == bigger_domain
      )

    if (nrow(bigger_word_pool) == 0) break

    for (j in sample(nrow(bigger_word_pool))) {
      bigger_word <- bigger_word_pool[j, ]
      smaller_word_pool <- size_dang_ranks |>
        filter(rep_count < 4) |>
        filter(
          size_rank < bigger_word$size_rank
        ) %>%
        {
          if (x$bigger_is_more_dangerous) {
            filter(., danger_rank < bigger_word$danger_rank)
          } else {
            filter(., danger_rank > bigger_word$danger_rank)
          }
        } |>
        filter(
          domain == smaller_domain
        )

      if (nrow(smaller_word_pool) > 0) break
    }

    if (nrow(smaller_word_pool) == 0) break

    smaller_word <- smaller_word_pool |>
      slice_sample(n = 1)

    word_pairs[, i] <- c(
      bigger_word$word,
      smaller_word$word
    )
    size_dang_ranks <- size_dang_ranks |>
      mutate(rep_count = if_else(word %in% word_pairs[, i], rep_count + 1, rep_count))
  }
  return(word_pairs)
}

