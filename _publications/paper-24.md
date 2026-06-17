---
title: "Predicted Incrementality by Experimentation (PIE) for Ad Measurement"
collection: publications
category: working-paper
permalink: /publication/2025-predictive-incrementality-pie
excerpt: ''
date: 2026-04-01
venue: 'Working Paper, available at arXiv'
paperurl: 'https://arxiv.org/abs/2304.06828'
citation: 'Gordon, B. R., Moakler, R., & Zettelmeyer, F. (2026). &quot;Predicted Incrementality by Experimentation (PIE) for Ad Measurement.&quot; <i>Management Science</i>, forthcoming.'
---

Randomized controlled trials (RCTs) provide the most credible estimates of advertising incrementality but are difficult to scale. We propose Predicted Incrementality by Experimentation (PIE), which reframes ad measurement as a campaign-level prediction problem. PIE uses a sample of RCTs to learn a mapping from campaign features to causal effects, then applies it to campaigns not run as RCTs. Because the RCTs identify the causal effects, PIE can incorporate post-determined features -- campaign-level aggregates such as test-group outcomes, exposure rates, and last-click conversions, computed after campaign completion. These metrics reflect the consumer behaviors that generate treatment effects, so they carry predictive information about incrementality even though they would be invalid controls in a causal model. Using 2,226 Meta ad experiments, PIE achieves an out-of-sample R^2=0.88 for incremental conversions per dollar, compared to R^2=0.19 for industry-standard 7-day last-click attribution. In a decision-making framework, PIE disagrees with RCT-based decisions in only 8-12% of campaigns, compared to 12-20% for last-click attribution. We conclude that PIE can help scale causal measurement from a limited number of RCTs to a large set of non-experimental campaigns.