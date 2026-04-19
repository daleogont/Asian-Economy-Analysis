// Requires both `npm start` (port 3000) and the Express backend (port 4000) to be running.

describe('Homepage', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('shows Asia Market Dashboard heading', () => {
    cy.contains('h1', 'Asia Market Dashboard').should('be.visible');
  });

  it('renders four summary stat cards', () => {
    cy.contains('Total Companies').should('be.visible');
    cy.contains('Avg Weekly Return').should('be.visible');
    cy.contains('Top Sector').should('be.visible');
    cy.contains('Largest Market').should('be.visible');
  });

  it('renders Markets by Country section', () => {
    cy.contains('Markets by Country').should('be.visible');
  });

  it('renders Top Movers table', () => {
    cy.contains('Top Movers (Weekly)').should('be.visible');
  });

  it('renders Sector Leaders table', () => {
    cy.contains('Sector Leaders').should('be.visible');
  });
});
