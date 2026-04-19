// Requires both `npm start` (port 3000) and the Express backend (port 4000) to be running.

describe('Country Page', () => {
  it('clicking a country card on homepage opens the country page', () => {
    cy.visit('/');
    cy.contains('Markets by Country').should('be.visible');
    cy.contains('Japan').click();
    cy.url().should('include', '/country/japan');
    cy.contains('h1', 'Japan').should('be.visible');
  });

  it('country page renders company table', () => {
    cy.visit('/country/japan');
    cy.contains('Company').should('be.visible');
    cy.contains('Sector').should('be.visible');
    cy.contains('Weekly Return (%)').should('be.visible');
  });

  it('clicking a company row shows Price History and Forecast tabs', () => {
    cy.visit('/country/japan');
    cy.get('table tbody tr').first().click();
    cy.contains('Price History').should('be.visible');
    cy.contains('Forecast').should('be.visible');
  });

  it('switching to Forecast tab shows forecast chart', () => {
    cy.visit('/country/japan');
    cy.get('table tbody tr').first().click();
    cy.contains('button', 'Forecast').click();
    cy.contains('Forecast').should('be.visible');
  });
});
