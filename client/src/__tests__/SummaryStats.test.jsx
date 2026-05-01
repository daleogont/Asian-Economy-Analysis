import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';
import SummaryStats from '../components/SummaryStats';

jest.mock('axios');

const mockStats = {
  companyCount: 42,
  price: { mean: 12345.67, median: 9800.5, std: 3200.1 },
  weeklyReturn: { mean: 1.23, max: 8.5, min: -4.2 },
};

afterEach(() => jest.clearAllMocks());

test('renders nothing before data loads', () => {
  axios.get.mockReturnValue(new Promise(() => {}));
  const { container } = render(<SummaryStats country="Japan" />);
  expect(container).toBeEmptyDOMElement();
});

test('renders Market Statistics heading with company count', async () => {
  axios.get.mockResolvedValue({ data: mockStats });
  render(<SummaryStats country="Japan" />);
  await waitFor(() =>
    expect(screen.getByText(/Market Statistics/)).toBeInTheDocument()
  );
  expect(screen.getByText(/42 companies/)).toBeInTheDocument();
});

test('renders mean, median and std price stat cards', async () => {
  axios.get.mockResolvedValue({ data: mockStats });
  render(<SummaryStats country="Japan" />);
  await waitFor(() => expect(screen.getByText('Avg Price')).toBeInTheDocument());
  expect(screen.getByText('Median Price')).toBeInTheDocument();
  expect(screen.getByText('Price Std Dev')).toBeInTheDocument();
});

test('renders weekly return stat cards', async () => {
  axios.get.mockResolvedValue({ data: mockStats });
  render(<SummaryStats country="Japan" />);
  await waitFor(() =>
    expect(screen.getByText('Avg Weekly Return')).toBeInTheDocument()
  );
  expect(screen.getByText('Best Weekly Return')).toBeInTheDocument();
  expect(screen.getByText('Worst Weekly Return')).toBeInTheDocument();
});

test('calls analytics API with country param', async () => {
  axios.get.mockResolvedValue({ data: mockStats });
  render(<SummaryStats country="South Korea" />);
  await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(1));
  expect(axios.get).toHaveBeenCalledWith(
    expect.stringContaining('country=South%20Korea')
  );
});

test('calls analytics API with sector param', async () => {
  axios.get.mockResolvedValue({ data: mockStats });
  render(<SummaryStats sector="Technology" />);
  await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(1));
  expect(axios.get).toHaveBeenCalledWith(
    expect.stringContaining('sector=Technology')
  );
});

test('renders nothing when API call fails', async () => {
  axios.get.mockRejectedValue(new Error('Network error'));
  const { container } = render(<SummaryStats country="Japan" />);
  await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(1));
  expect(container).toBeEmptyDOMElement();
});
