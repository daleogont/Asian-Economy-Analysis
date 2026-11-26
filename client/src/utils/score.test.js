import { computeScore, DEFAULT_BUDGETS } from "./score";

describe("computeScore", () => {
  test("the most accurate model within every budget scores exactly 100", () => {
    const score = computeScore(
      13.1653, 13.1653,
      { latencyMs: 156.9, trainTimeS: 0.339, memoryMb: 0.48 },
      DEFAULT_BUDGETS
    );
    expect(score).toBeCloseTo(100, 4);
  });

  test("a less accurate but within-budget model scores below 100 by the accuracy ratio alone", () => {
    const score = computeScore(
      13.3555, 13.1653,
      { latencyMs: 92.6, trainTimeS: 0.419, memoryMb: 0.86 },
      DEFAULT_BUDGETS
    );
    expect(score).toBeCloseTo((13.1653 / 13.3555) * 100, 2);
  });

  test("a model far outside multiple budgets is penalized multiplicatively", () => {
    const score = computeScore(
      18.0727, 13.1653,
      { latencyMs: 110.7, trainTimeS: 21.573, memoryMb: 47.50 },
      DEFAULT_BUDGETS
    );
    // accuracy * (200/110.7 capped at 1) * (2/21.573) * (10/47.50)
    const expected = 100 * (13.1653 / 18.0727) * 1 * (2 / 21.573) * (10 / 47.50);
    expect(score).toBeCloseTo(expected, 4);
  });

  test("being cheaper than the budget gives no bonus (ratio caps at 1)", () => {
    const cheap = computeScore(10, 10, { latencyMs: 1, trainTimeS: 0.01, memoryMb: 0.01 }, DEFAULT_BUDGETS);
    expect(cheap).toBeCloseTo(100, 4);
  });

  test("a zero or negative budget with a positive cost drives the score to 0", () => {
    const score = computeScore(10, 10, { latencyMs: 50, trainTimeS: 1, memoryMb: 1 }, { ...DEFAULT_BUDGETS, latencyMs: 0 });
    expect(score).toBe(0);
  });

  test("returns null when rmse is missing or non-positive", () => {
    expect(computeScore(null, 10, {}, DEFAULT_BUDGETS)).toBeNull();
    expect(computeScore(0, 10, {}, DEFAULT_BUDGETS)).toBeNull();
    expect(computeScore(-5, 10, {}, DEFAULT_BUDGETS)).toBeNull();
  });

  test("widening a budget can only raise or hold a score, never lower it", () => {
    const costs = { latencyMs: 400, trainTimeS: 5, memoryMb: 20 };
    const narrow = computeScore(10, 10, costs, DEFAULT_BUDGETS);
    const wide = computeScore(10, 10, costs, { latencyMs: 1000, trainTimeS: 10, memoryMb: 50 });
    expect(wide).toBeGreaterThanOrEqual(narrow);
  });
});
