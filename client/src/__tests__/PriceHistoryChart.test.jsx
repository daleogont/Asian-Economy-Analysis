import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import axios from 'axios';
import PriceHistoryChart from '../components/PriceHistoryChart';

jest.mock('axios');
jest.mock('recharts', () => {
  const React = require('react');
  const Wrap = ({ children }) => React.createElement('div', { 'data-testid': 'recharts-wrapper' }, children);
  const Empty = () => null;
  return { ResponsiveContainer: Wrap, LineChart: Wrap, BarChart: Wrap, Line: Empty, Bar: Empty, XAxis: Empty, YAxis: Empty, CartesianGrid: Empty, Tooltip: Empty, Legend: Empty, Cell: Empty };
});

const mockData = {
  data: [
    { date: '2024-01-01', close: 100, ma30: 98 },
    { date: '2024-01-08', close: 102, ma30: 99 },
    { date: '2024-01-15', close: 105, ma30: 101 },
  ],
};

afterEach(() => jest.clearAllMocks());

test('renders nothing when no ticker is provided', () => {
  const { container } = render(<PriceHistoryChart />);
  expect(container).toBeEmptyDOMElement();
});

test('renders Price History heading with ticker', async () => {
  axios.get.mockResolvedValue({ data: mockData });
  render(<PriceHistoryChart ticker="TSLA" />);
  await waitFor(() =>
    expect(screen.getByText('Price History — TSLA')).toBeInTheDocument()
  );
});

test('renders all four period buttons', async () => {
  axios.get.mockResolvedValue({ data: mockData });
  render(<PriceHistoryChart ticker="TSLA" />);
  await waitFor(() => expect(screen.getByText('3M')).toBeInTheDocument());
  expect(screen.getByText('6M')).toBeInTheDocument();
  expect(screen.getByText('1Y')).toBeInTheDocument();
  expect(screen.getByText('2Y')).toBeInTheDocument();
});

test('renders rolling average buttons', async () => {
  axios.get.mockResolvedValue({ data: mockData });
  render(<PriceHistoryChart ticker="TSLA" />);
  await waitFor(() => expect(screen.getByText('Off')).toBeInTheDocument());
  expect(screen.getByText('7d')).toBeInTheDocument();
  expect(screen.getByText('30d')).toBeInTheDocument();
});

test('calls API with default period 1y', async () => {
  axios.get.mockResolvedValue({ data: mockData });
  render(<PriceHistoryChart ticker="AAPL" />);
  await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(1));
  expect(axios.get).toHaveBeenCalledWith(
    expect.stringContaining('/analytics/rolling/AAPL')
  );
  expect(axios.get).toHaveBeenCalledWith(
    expect.stringContaining('period=1y')
  );
});

test('clicking a period button refetches data', async () => {
  axios.get.mockResolvedValue({ data: mockData });
  render(<PriceHistoryChart ticker="AAPL" />);
  await waitFor(() => expect(screen.getByText('3M')).toBeInTheDocument());

  fireEvent.click(screen.getByText('3M'));
  await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(2));
  expect(axios.get).toHaveBeenLastCalledWith(
    expect.stringContaining('period=3m')
  );
});

test('renders chart wrapper after data loads', async () => {
  axios.get.mockResolvedValue({ data: mockData });
  render(<PriceHistoryChart ticker="AAPL" />);
  await waitFor(() =>
    expect(screen.getAllByTestId('recharts-wrapper').length).toBeGreaterThan(0)
  );
});
