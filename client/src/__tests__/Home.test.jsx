import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import Home from '../pages/Home';

jest.mock('axios');
jest.mock('recharts', () => {
  const React = require('react');
  const Wrap = ({ children }) => React.createElement('div', null, children);
  const Empty = () => null;
  return { ResponsiveContainer: Wrap, LineChart: Wrap, BarChart: Wrap, Line: Empty, Bar: Empty, XAxis: Empty, YAxis: Empty, CartesianGrid: Empty, Tooltip: Empty, Legend: Empty, Cell: Empty };
});
jest.mock('../components/WeeklyReturnHistogram', () => () => (
  <div data-testid="weekly-histogram" />
));

const mockCompanies = [
  { ticker: 'J001', name: 'Toyota', country: 'Japan', sector: 'Technology', stockPrice: 15000, weeklyReturn: 2.5 },
  { ticker: 'C001', name: 'Alibaba', country: 'China', sector: 'Finance', stockPrice: 8000, weeklyReturn: -1.0 },
];
const mockSectors = [
  { name: 'Technology', companyCount: 50 },
  { name: 'Finance', companyCount: 30 },
];
const mockCountries = [
  { country: 'Japan', companyCount: 80, averageWeeklyReturn: 1.2 },
  { country: 'China', companyCount: 120, averageWeeklyReturn: -0.5 },
];
const mockTopMovers = [
  { ticker: 'J001', name: 'Toyota', country: 'Japan', weeklyReturn: 2.5 },
];
const mockSectorLeaders = [
  { ticker: 'J001', name: 'Toyota', sector: 'Technology', stockPrice: 15000 },
];

const setup = async () => {
  await act(async () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );
  });
};

beforeEach(() => {
  axios.get.mockImplementation((url) => {
    if (url === '/api/companies') return Promise.resolve({ data: mockCompanies });
    if (url === '/api/sectors') return Promise.resolve({ data: mockSectors });
    if (url === '/api/countries') return Promise.resolve({ data: mockCountries });
    if (url === '/api/top-movers') return Promise.resolve({ data: mockTopMovers });
    if (url === '/api/sector-leaders') return Promise.resolve({ data: mockSectorLeaders });
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
});

afterEach(() => jest.clearAllMocks());

test('renders Asia Market Dashboard heading', async () => {
  await setup();
  expect(screen.getByText('Asia Market Dashboard')).toBeInTheDocument();
});

test('renders all four stat card labels', async () => {
  await setup();
  expect(screen.getByText('Total Companies')).toBeInTheDocument();
  expect(screen.getByText('Avg Weekly Return')).toBeInTheDocument();
  expect(screen.getByText('Top Sector')).toBeInTheDocument();
  expect(screen.getByText('Largest Market')).toBeInTheDocument();
});

test('renders Markets by Country section heading', async () => {
  await setup();
  expect(screen.getByText('Markets by Country')).toBeInTheDocument();
});

test('shows total company count after data loads', async () => {
  await setup();
  expect(screen.getByText('2')).toBeInTheDocument();
});

test('shows top sector name after data loads', async () => {
  await setup();
  expect(screen.getAllByText('Technology').length).toBeGreaterThan(0);
});

test('shows largest market after data loads', async () => {
  await setup();
  expect(screen.getAllByText(/China/).length).toBeGreaterThan(0);
});

test('renders country grid cards after data loads', async () => {
  await setup();
  expect(screen.getByText('Japan')).toBeInTheDocument();
  expect(screen.getByText('China')).toBeInTheDocument();
});

test('renders weekly histogram after companies load', async () => {
  await setup();
  expect(screen.getByTestId('weekly-histogram')).toBeInTheDocument();
});

test('renders Top Movers and Sector Leaders table headings', async () => {
  await setup();
  expect(screen.getByText('Top Movers (Weekly)')).toBeInTheDocument();
  expect(screen.getByText('Sector Leaders')).toBeInTheDocument();
});
