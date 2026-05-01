import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import CountryPage from '../components/CountryPage';

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
  { ticker: 'J001', name: 'Toyota', country: 'Japan', sector: 'Consumer Discretionary', stockPrice: 15000, weeklyReturn: 2.5, marketCap: 30000000 },
  { ticker: 'J002', name: 'Sony', country: 'Japan', sector: 'Technology', stockPrice: 12000, weeklyReturn: 1.8, marketCap: 20000000 },
  { ticker: 'C001', name: 'Alibaba', country: 'China', sector: 'Finance', stockPrice: 8000, weeklyReturn: -1.0, marketCap: 15000000 },
];
const mockMacro = { gdp: 4231, population: 125, unemployment: 2.6 };

const setup = (country = 'Japan') =>
  render(
    <MemoryRouter>
      <CountryPage country={country} />
    </MemoryRouter>
  );

beforeEach(() => {
  axios.get.mockImplementation((url) => {
    if (url === '/api/companies') return Promise.resolve({ data: mockCompanies });
    if (url.startsWith('/api/macros')) return Promise.resolve({ data: mockMacro });
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
});

afterEach(() => jest.clearAllMocks());

test('renders country name as heading after data loads', async () => {
  setup('Japan');
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'Japan' })).toBeInTheDocument()
  );
});

test('renders company table with column headers', async () => {
  setup('Japan');
  await waitFor(() => {
    expect(screen.getByText('Company')).toBeInTheDocument();
    expect(screen.getByText('Sector')).toBeInTheDocument();
  });
});

test('renders only companies for the given country', async () => {
  setup('Japan');
  await waitFor(() => {
    expect(screen.getByText('Toyota')).toBeInTheDocument();
    expect(screen.getByText('Sony')).toBeInTheDocument();
  });
  expect(screen.queryByText('Alibaba')).not.toBeInTheDocument();
});

test('renders macro indicator cards', async () => {
  setup('Japan');
  await waitFor(() =>
    expect(screen.getAllByText(/4,231|4231/).length).toBeGreaterThan(0)
  );
});

test('renders SummaryStats component', async () => {
  setup('Japan');
  await waitFor(() =>
    expect(screen.getByTestId('summary-stats')).toBeInTheDocument()
  );
});

test('clicking a company row shows Price History and Forecast tabs', async () => {
  setup('Japan');
  await waitFor(() => expect(screen.getByText('Toyota')).toBeInTheDocument());

  fireEvent.click(screen.getByText('Toyota').closest('tr'));
  expect(screen.getByText('Price History')).toBeInTheDocument();
  expect(screen.getByText('Forecast')).toBeInTheDocument();
});

test('clicking a company row shows PriceHistoryChart by default', async () => {
  setup('Japan');
  await waitFor(() => expect(screen.getByText('Toyota')).toBeInTheDocument());

  fireEvent.click(screen.getByText('Toyota').closest('tr'));
  expect(screen.getByTestId('price-history-J001')).toBeInTheDocument();
});

test('switching to Forecast tab shows ForecastChart', async () => {
  setup('Japan');
  await waitFor(() => expect(screen.getByText('Toyota')).toBeInTheDocument());

  fireEvent.click(screen.getByText('Toyota').closest('tr'));
  fireEvent.click(screen.getByText('Forecast'));
  expect(screen.getByTestId('forecast-J001')).toBeInTheDocument();
});

test('shows no data message when country has no companies', async () => {
  setup('UnknownCountry');
  await waitFor(() =>
    expect(screen.getByText(/No data available for UnknownCountry/)).toBeInTheDocument()
  );
});
