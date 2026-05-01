import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import SectionPage from '../components/SectionPage';

jest.mock('axios');
jest.mock('recharts', () => {
  const React = require('react');
  const Wrap = ({ children }) => React.createElement('div', null, children);
  const Empty = () => null;
  return { ResponsiveContainer: Wrap, LineChart: Wrap, BarChart: Wrap, Line: Empty, Bar: Empty, XAxis: Empty, YAxis: Empty, CartesianGrid: Empty, Tooltip: Empty, Legend: Empty, Cell: Empty };
});
jest.mock('../components/SummaryStats', () => () => <div data-testid="summary-stats" />);
jest.mock('../components/WeeklyReturnHistogram', () => () => <div data-testid="weekly-histogram" />);
jest.mock('../components/PriceHistoryChart', () => ({ ticker }) => (
  <div data-testid={`price-history-${ticker}`}>Price History Chart</div>
));
jest.mock('../components/ForecastChart', () => ({ ticker }) => (
  <div data-testid={`forecast-${ticker}`}>Forecast Chart</div>
));

const mockCompanies = [
  { ticker: 'T001', name: 'Samsung', country: 'South Korea', sector: 'Technology', stockPrice: 70000, weeklyReturn: 1.5, marketCap: 400000000 },
  { ticker: 'T002', name: 'TSMC', country: 'Taiwan', sector: 'Technology', stockPrice: 900, weeklyReturn: 2.1, marketCap: 300000000 },
  { ticker: 'F001', name: 'ICBC', country: 'China', sector: 'Finance', stockPrice: 5, weeklyReturn: 0.5, marketCap: 200000000 },
];

const setup = (sector = 'Technology') =>
  render(
    <MemoryRouter>
      <SectionPage sector={sector} />
    </MemoryRouter>
  );

beforeEach(() => {
  axios.get.mockImplementation((url) => {
    if (url === '/api/companies') return Promise.resolve({ data: mockCompanies });
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
});

afterEach(() => jest.clearAllMocks());

test('renders sector name as heading after data loads', async () => {
  setup('Technology');
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'Technology' })).toBeInTheDocument()
  );
});

test('renders company table with column headers', async () => {
  setup('Technology');
  await waitFor(() => {
    expect(screen.getByText('Company')).toBeInTheDocument();
    expect(screen.getByText('Country')).toBeInTheDocument();
  });
});

test('renders only companies for the given sector', async () => {
  setup('Technology');
  await waitFor(() => {
    expect(screen.getByText('Samsung')).toBeInTheDocument();
    expect(screen.getByText('TSMC')).toBeInTheDocument();
  });
  expect(screen.queryByText('ICBC')).not.toBeInTheDocument();
});

test('shows sector leader line with highest market cap company', async () => {
  setup('Technology');
  await waitFor(() =>
    expect(screen.getByText(/Sector leader: Samsung/)).toBeInTheDocument()
  );
});

test('renders SummaryStats component', async () => {
  setup('Technology');
  await waitFor(() =>
    expect(screen.getByTestId('summary-stats')).toBeInTheDocument()
  );
});

test('renders weekly histogram after data loads', async () => {
  setup('Technology');
  await waitFor(() =>
    expect(screen.getByTestId('weekly-histogram')).toBeInTheDocument()
  );
});

test('clicking a company row shows Price History and Forecast tabs', async () => {
  setup('Technology');
  await waitFor(() => expect(screen.getByText('Samsung')).toBeInTheDocument());

  fireEvent.click(screen.getByText('Samsung').closest('tr'));
  expect(screen.getByText('Price History')).toBeInTheDocument();
  expect(screen.getByText('Forecast')).toBeInTheDocument();
});

test('clicking expanded row again collapses it', async () => {
  setup('Technology');
  await waitFor(() => expect(screen.getByText('Samsung')).toBeInTheDocument());

  const row = screen.getByText('Samsung').closest('tr');
  fireEvent.click(row);
  expect(screen.getByTestId('price-history-T001')).toBeInTheDocument();

  fireEvent.click(row);
  expect(screen.queryByTestId('price-history-T001')).not.toBeInTheDocument();
});

test('shows no data message when sector has no companies', async () => {
  setup('UnknownSector');
  await waitFor(() =>
    expect(screen.getByText(/No data available for UnknownSector/)).toBeInTheDocument()
  );
});
