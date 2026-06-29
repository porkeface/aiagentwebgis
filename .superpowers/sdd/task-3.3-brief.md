# Task 3.3: MMR Diversity Rerank

**Files:**
- Create: `backend/recommendation/mmr.py`
- Test: `backend/tests/test_recommendation/test_mmr.py`

**Consumes:** scored POI list, lambda parameter, selection count
**Produces:** diverse POI subset

**Steps:**

1. Implement mmr_rerank(pois, lambda_=0.7, k=10):
   - For each iteration, select POI maximizing: lambda * relevance - (1-lambda) * max_similarity_to_selected
   - Similarity: category overlap (Jaccard)
   - Continue until k POIs selected or pool exhausted

2. Write tests:
   - test_mmr_selects_diverse_categories: input has 8 temples + 2 museums, MMR picks museums
   - test_mmr_respects_lambda_zero: lambda=0 -> pure diversity
   - test_mmr_respects_lambda_one: lambda=1 -> pure relevance

3. Run tests, commit: `feat: MMR diversity rerank for category-balanced recommendations`
