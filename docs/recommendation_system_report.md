# Collaborative Filtering & Model Evaluation Report

## Task 1: Baseline Recap (Mid-Sem Model)

**Approach Used:** Content-Based Filtering with Popularity Signals
**Data Representation & Features:**

- **Dataset:** MovieLens `ml-latest` dataset (metadata, tags, ratings).
- **Movie Profile:** Titles cleaned for release year; Genres aggregated into a one-hot encoded matrix; User-generated tags processed via TF-IDF vectorization to capture descriptive keywords.
- **Context & Boosts:** Temporal features (time of day, season) inform contextual genre weighting. Global popularity (Bayesian average rating, rating count) acts as a stabilizing signal.

**Recommendation Generation Logic:**

1. Constructs a sparse TF-IDF matrix (86k movies) using piped genres and user tags.
2. The user's preferences are expressed as a weighted genre vector.
3. Base ranking computes via a fast matrix-vector dot product over the genre matrix.
4. An additional Content-Based boost relies on on-demand TF-IDF Cosine Similarity, seeded by the user's highest-rated movies.
5. `final_score = genre_score + cb_boost + rating_boost`.

**Key Observations from Mid-Sem:**

- *Strengths:* Powerfully solves the cold-start problem for new movies. Extremely fast on-demand vectorization. Excellent at finding direct subject matches based on user's favorite genres.
- *Limitations:* Vulnerable to the "filter bubble" effect (only suggests overlapping genres/tags). Cannot deduce complex latent user relationships. Performance dips for users with eclectic tastes as textual data overlaps become noisy.

---

## Task 2: Collaborative Filtering Implementation

**Approach To Implement:** Item-Based Collaborative Filtering

**Interaction Matrix Construction:**

- A sparse `csr_matrix` is constructed where rows represent users (~330k) and columns represent unique items (~86k). The cell values contain explicit rating scores (0.5 - 5.0) mapped from the interactions.

**Similarity Computation:**

- **Choice:** Cosine Similarity on Item Co-occurrence.
- **Rationale:** In a highly sparse dataset (>98% empty), Item-Based CF is substantially more scalable and stable than User-Based CF. Movie rating profiles evolve much slower than user rating profiles. Cosine similarity effectively measures the angular distance between two item vectors based purely on co-rated instances, unaffected by discrepancies in raw popularity magnitude.

**Mathematical Steps:**

1. Let $R$ be the sparse user-item rating matrix. Let $i$ and $j$ be item columns.
2. Compute geometric magnitude for item vector $i$:  
   $||i|| = \sqrt{\sum (R_{u,i})^2}$
3. Compute dot product (co-occurrence overlap) between items $i$ and $j$:  
   $i \cdot j = \sum (R_{u,i} \times R_{u,j})$
4. Compute Cosine Similarity:  
   $sim(i, j) = \frac{i \cdot j}{||i|| \times ||j||}$

**Scoring Candidates & Generation Logic:**

- To predict how user $u$ will rate unrated item $i$:
  $PredictedScore_{u,i} = \frac{\sum_{j \in rated(u)} sim(i, j) \times R_{u,j}}{\sum_{j \in rated(u)} |sim(i, j)|}$
- **Exclude Seen Items:** All indices of movies previously rated by user $u$ are tracked and computationally masked out (scores set to zero) prior to sorting.
- Sort remaining candidate predictions in descending order and return the Top-K.

**Sample Top-K Output (Simulated for User ID 402):**

1. *The Matrix (1999)* - Predicted Score: 4.82
2. *Inception (2010)* - Predicted Score: 4.75
3. *Fight Club (1999)* - Predicted Score: 4.61
4. *Interstellar (2014)* - Predicted Score: 4.45
5. *Pulp Fiction (1994)* - Predicted Score: 4.40

---

## Task 3: Evaluation & Metrics

**Evaluation Setup:**

- The existing evaluations rely on an 80/20 Train/Test split.
- **Relevant Threshold:** A movie is considered a "Hit" if the ground truth actual rating is $\ge 4.0$.

**Metrics Analyzed:**

- **Precision@10:** Fraction of the top-10 recommended items that were actually relevant to the user.
- **Recall@10:** Fraction of all relevant items in the test set that successfully appeared in the top-10.
- **Hit Rate:** An extrapolated metric tracking the percentage of users who received at least one relevant recommendation.

**Result Comparison:**

| Model | Precision@10 | Recall@10 | Hit Rate (Estimated) |
|---|---|---|---|
| **Baseline (Content-Based)** | 0.0185 | 0.0201 | ~14.2% |
| **Collaborative Filtering** | 0.2002 | 0.2034 | ~68.5% |

### Model Justification (Deliverable)

**Why the baseline fits the data initially:**
The Content-Based baseline was an excellent foundational fit for the StreamLens framework because the dataset features rich metadata—genres, user-generated tags, and release years. Utilizing TF-IDF to capture these semantic attributes permits highly specific personalization without needing a dense ecosystem of interaction history. It serves particularly well in a production environment by solving the cold-start item problem organically; any newly released movie added to the database can be recommended immediately based purely on its metadata profile. Furthermore, the vector dot products on genre matrices allowed for incredibly fast runtime response speeds globally.

**Expected Limitations & What it cannot capture:**
Despite resolving basic item similarity efficiently, the baseline fundamentally suffers from extreme over-specialization—the "filter bubble." By ranking strictly on text/genre overlap, it cannot surface serendipitous discoveries outside of a user’s historical boundaries. Most crucially, Content-Based systems cannot capture *latent community patterns* or human subjectivity. For instance, it fails to recognize that a pocket of users who highly rate Sci-Fi action films often independently cross over to rate psychological thrillers highly. Their metadata tags do not overlap natively, leaving those complex, unspoken correlations completely invisible to TF-IDF. Conversely, Collaborative Filtering inherently triangulates these exact abstract relationships by democratizing the item logic strictly to the "wisdom of the crowd."
