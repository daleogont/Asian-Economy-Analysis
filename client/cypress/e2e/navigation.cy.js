// Requires both `npm start` (port 3000) and the Express backend (port 4000) to be running.

describe('Navigation', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('navigates to Countries page', () => {
    cy.visit('/countries');
    cy.url().should('include', '/countries');
    cy.contains('Countries').should('be.visible');
  });

  it('navigates to Sections page', () => {
    cy.visit('/sections');
    cy.url().should('include', '/sections');
    cy.contains('Sectors').should('be.visible');
  });

  it('navigates to Research page', () => {
    cy.visit('/research');
    cy.url().should('include', '/research');
    cy.get('main, [class*="px-"], h1, h2').should('exist');
  });

  it('navigates to a country page via subheader link', () => {
    cy.visit('/country/japan');
    cy.url().should('include', '/country/japan');
    cy.contains('h1', 'Japan').should('be.visible');
  });

  it('navigates to a section page via direct URL', () => {
    cy.visit('/section/financials');
    cy.url().should('include', '/section/financials');
    cy.contains('h1', /Financials/i).should('be.visible');
  });
});
