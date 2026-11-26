export const DEFAULT_BUDGETS = { latencyMs: 200, trainTimeS: 2, memoryMb: 10 };

/**
 * min(1, budget/cost): 1 while within budget (no bonus for being cheaper),
 * shrinks proportionally once over. A non-positive cost is treated as free
 * (ratio 1); a non-positive budget with a positive cost is treated as an
 * unaffordable budget (ratio 0).
 */
function budgetRatio(cost, budget) {
  if (cost == null || cost <= 0) return 1;
  if (budget <= 0) return 0;
  return Math.min(1, budget / cost);
}

/**
 * Score = 100 * (RMSE_min / RMSE) * product of min(1, budget_j / cost_j).
 * 100 only for the most accurate model in the current comparison AND
 * within every budget. Returns null when rmse/rmseMin aren't usable.
 */
export function computeScore(rmse, rmseMin, costs, budgets) {
  if (rmse == null || rmseMin == null || rmse <= 0 || rmseMin <= 0) return null;
  const accuracyRatio = rmseMin / rmse;
  const penalty =
    budgetRatio(costs.latencyMs, budgets.latencyMs) *
    budgetRatio(costs.trainTimeS, budgets.trainTimeS) *
    budgetRatio(costs.memoryMb, budgets.memoryMb);
  return 100 * accuracyRatio * penalty;
}
