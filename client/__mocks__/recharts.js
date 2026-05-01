const React = require('react');

const Wrap = ({ children }) => React.createElement('div', { 'data-testid': 'recharts-wrapper' }, children);
const Empty = () => null;

module.exports = {
  ResponsiveContainer: Wrap,
  LineChart: Wrap,
  BarChart: Wrap,
  Line: Empty,
  Bar: Empty,
  XAxis: Empty,
  YAxis: Empty,
  CartesianGrid: Empty,
  Tooltip: Empty,
  Legend: Empty,
  Cell: Empty,
  ReferenceLine: Empty,
};
