# Step 11.5 -- Model Theory: Financial Health Scoring

## 1. Problem Statement

Given a company's financial ratios extracted from its IPO prospectus, assign
a quantitative Financial Health Score (0--100) that indicates how the company
compares to other IPO companies. The score must be:

- **Interpretable.** A non-technical user should understand what "score = 75"
  means without studying the algorithm.
- **Sector-aware.** A debt-to-equity ratio of 2.0 may be normal for
  infrastructure companies but alarming for IT services.
- **Robust to missing data.** RHP text extraction via regex will frequently
  produce `null` values for some metrics.

---

## 2. Methodology: Percentile Ranking

The health score is computed using **percentile ranking**, not a trained
machine learning model. This approach was chosen for its transparency and
simplicity.

### Definition

For a given metric (e.g., EBITDA margin), the percentile rank is the
proportion of companies in the reference group whose metric value is less
than or equal to the target company's value:

```
percentile = count(dataset_value <= company_value) / total_companies
```

For metrics where lower is better (e.g., debt-to-equity), the direction is
inverted:

```
percentile = count(dataset_value >= company_value) / total_companies
```

The final health score is the **arithmetic mean of all available percentile
ranks**, scaled to 0--100:

```
score = mean(percentile_1, percentile_2, ..., percentile_n) * 100
```

### Interpretation

A score of 75 means: "This company's average financial metric is better than
75% of companies in the comparison group." This is directly communicable to
end users without any statistical background.

---

## 3. Feature Pipeline

### 3.1 Input: Financial Ratios

The financial extractor (`financial_extractor.py`) produces three ratios from
regex-extracted metrics:

| Ratio               | Formula                      | Higher = Better? |
|----------------------|------------------------------|------------------|
| `net_profit_margin`  | PAT / Revenue                | Yes              |
| `ebitda_margin`      | EBITDA / Revenue             | Yes              |
| `debt_to_equity`     | Total Debt / Net Worth       | No (lower = better) |

### 3.2 Mapping to Training Dataset Keys

The training dataset uses different key names than the extracted ratios. The
mapping is:

| Extracted Ratio Key  | Training Dataset Key       |
|----------------------|----------------------------|
| `ebitda_margin`      | `ebitda_margin_avg`        |
| `net_profit_margin`  | `pat_margin_avg`           |
| `debt_to_equity`     | `debt_to_equity_latest`    |

### 3.3 Full Metric Universe

The training dataset contains 9 metrics per company. The health score engine
can compute percentiles for any of these, but only 3 are derivable from the
current regex extraction pipeline:

| Training Metric Key        | Available from Regex? | Higher = Better? |
|----------------------------|-----------------------|------------------|
| `ebitda_margin_avg`        | Yes                   | Yes              |
| `pat_margin_avg`           | Yes                   | Yes              |
| `revenue_cagr`             | No                    | Yes              |
| `pat_cagr`                 | No                    | Yes              |
| `current_ratio_latest`     | No                    | Yes              |
| `debt_to_equity_latest`    | Yes                   | No               |
| `interest_coverage_latest` | No                    | Yes              |
| `asset_turnover_latest`    | No                    | Yes              |
| `ocf_to_pat_avg`           | No                    | Yes              |

When a metric is not available (either because regex extraction failed or the
mapping does not exist), it is simply excluded from the percentile average.
This means the score adapts to whatever data is available.

---

## 4. Sector Detection and Fallback

### 4.1 Sector Detection

The health score engine scans the first 100,000 characters of the RHP text
file for sector keywords using regex patterns:

```
"Industry: IT Services"
"Sector - Financial Services"
"Business Overview ... Manufacturing"
```

Supported sector keywords include: Manufacturing, Financial Services,
IT Services, Pharmaceuticals, FMCG, Healthcare, Infrastructure, Real Estate,
Chemicals, Textiles, Media, Energy, Retail, Logistics, Mining.

### 4.2 Sector Filtering

If a sector is detected, the training dataset is filtered to include only
companies in that sector. Percentile ranks are then computed within this
sector-specific subset.

### 4.3 GLOBAL Fallback

If the sector is not detected (regex finds no match) or the detected sector
has no entries in the training dataset, the system falls back to the entire
dataset ("GLOBAL"). The response includes a `fallback_used: true` flag to
indicate this.

**Why this matters:** Comparing a pharmaceutical company's margins against a
construction company's margins is misleading. Sector filtering ensures that
the percentile ranking reflects industry norms. The GLOBAL fallback is a
safety net that prevents the system from failing when sector detection is
imprecise.

---

## 5. Score Categories

| Score Range | Category  | Interpretation                            |
|-------------|-----------|-------------------------------------------|
| 0 -- 39     | Weak      | Below average financial health            |
| 40 -- 70    | Average   | Moderate financial standing               |
| 71 -- 100   | Strong    | Above average financial health            |

When no features are available at all (all metrics are `null`), a default
score of 50.0 ("Average") is assigned.

---

## 6. Worked Example

Assume a company has the following extracted ratios:

```
net_profit_margin = 0.12  (12%)
ebitda_margin     = 0.25  (25%)
debt_to_equity    = 0.80
```

And the GLOBAL training dataset (68 companies) has these distributions:

**PAT margin (`pat_margin_avg`):**
- 42 out of 68 companies have pat_margin_avg <= 0.12
- Percentile = 42 / 68 = 0.6176

**EBITDA margin (`ebitda_margin_avg`):**
- 51 out of 68 companies have ebitda_margin_avg <= 0.25
- Percentile = 51 / 68 = 0.7500

**Debt-to-equity (`debt_to_equity_latest`, lower is better):**
- 55 out of 68 companies have debt_to_equity_latest >= 0.80
- Percentile = 55 / 68 = 0.8088

**Final score:**
```
score = mean(0.6176, 0.7500, 0.8088) * 100
      = 0.7255 * 100
      = 72.55 --> Category: "Strong"
```

---

## 7. Output Format

### Clean Mode (`debug=false`)

```json
{
  "company_name": "Example Corp",
  "sector_used": "GLOBAL",
  "score": 72.55,
  "category": "Strong",
  "peer_percentile": 0.7255,
  "explanation": "This company is financially stronger than 72% of companies
                  in the same sector. (GLOBAL fallback used)"
}
```

### Debug Mode (`debug=true`)

```json
{
  "company_name": "Example Corp",
  "sector_detected": null,
  "sector_used": "GLOBAL",
  "fallback_used": true,
  "total_companies_used": 68,
  "score": 72.55,
  "category": "Strong",
  "features_used": ["pat_margin_avg", "ebitda_margin_avg", "debt_to_equity_latest"],
  "feature_percentiles": {
    "pat_margin_avg": 0.6176,
    "ebitda_margin_avg": 0.7500,
    "debt_to_equity_latest": 0.8088
  }
}
```

---

## 8. Comparison with Alternative Approaches

| Approach            | Pros                           | Cons                                  |
|---------------------|--------------------------------|---------------------------------------|
| **Percentile rank** | Transparent, no training, handles missing data | Depends on reference dataset quality |
| Random Forest       | Can capture non-linear relationships | Needs labelled data, black-box   |
| Weighted average    | Simple, customisable weights   | Weights are arbitrary, not data-driven |
| Z-score             | Standard statistical method    | Assumes normal distribution; hard to interpret for users |

Percentile ranking was chosen because it provides the best balance of
interpretability and robustness for a project where the primary audience
is retail investors and interview evaluators.

---

## 9. Limitations

1. **Training dataset size.** With ~68 companies, percentile granularity is
   limited. The smallest non-zero percentile is 1/68 = 1.5%. A larger dataset
   would provide finer discrimination.

2. **Only 3 out of 9 metrics are extracted.** The regex pipeline currently
   extracts only revenue, PAT, EBITDA, total assets, net worth, total debt,
   and EPS. Of these, only 3 ratios map to training dataset keys. Expanding
   the extraction pipeline would improve score reliability.

3. **Equal weighting.** All available features contribute equally to the final
   score. In reality, some metrics (e.g., cash flow) may be more predictive
   of financial health than others (e.g., EPS).

4. **Sector detection is regex-based.** It depends on the RHP text containing
   explicit sector keywords. Many prospectuses do not state the sector
   clearly, leading to frequent GLOBAL fallback.

---

## 10. Viva Preparation: Key Questions

**Q: Why percentile ranking instead of a neural network or random forest?**
A: Percentile ranking is fully transparent. A score of 75 directly means
"better than 75% of peers." No training step is needed, no hyperparameters
to tune, and no risk of overfitting on a small dataset.

**Q: What happens when only 1 out of 3 ratios is available?**
A: The score is computed using just that one ratio's percentile. The system
does not fail; it produces a less reliable but still valid score.

**Q: How is sector-awareness achieved?**
A: The training dataset is filtered by sector before computing percentiles.
If only 12 companies in "IT Services" are available, percentiles are computed
within those 12. If the sector is unknown, the full dataset (~68 companies) is
used as a fallback.

**Q: Could this approach produce a score of 100?**
A: Yes, if the company's metrics are better than all companies in the
reference group for every available feature. This would mean its average
percentile is 1.0, yielding a score of 100.

**Q: Is this supervised or unsupervised learning?**
A: Strictly speaking, percentile ranking is neither. It is a statistical
comparison method. There is no model being trained. The training dataset
is used as a reference distribution, not as labelled training data in the
machine learning sense.
