/**
 * Non-dominated set for two values to minimize (e.g. train time + RMSE):
 * a point is on the front if no other point is <= it on both axes with a
 * strictly lower value on at least one.
 */
export function paretoFront(points, xKey, yKey) {
  return points.filter((p) => {
    return !points.some((q) => {
      if (q === p) return false;
      const notWorse = q[xKey] <= p[xKey] && q[yKey] <= p[yKey];
      const strictlyBetter = q[xKey] < p[xKey] || q[yKey] < p[yKey];
      return notWorse && strictlyBetter;
    });
  });
}
