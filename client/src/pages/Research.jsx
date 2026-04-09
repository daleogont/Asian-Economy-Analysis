import React, { useState } from "react";

const ALL_COUNTRIES = [
  "Japan", "China", "India", "Thailand", "Singapore",
  "South Korea", "Malaysia", "Indonesia", "Taiwan", "Saudi Arabia",
];

const groupedArticles = {
  "Japan": [
    {
      title: "Transforming Japan Real Estate",
      source: "arXiv",
      description: "Analysis of Japan's real estate market and the influence of conglomerates.",
      link: "https://arxiv.org/abs/2405.20715",
    },
    {
      title: "Keiretsu",
      source: "Wikipedia",
      description: "Overview of Japanese corporate groups (Keiretsu) and their structure.",
      link: "https://en.wikipedia.org/wiki/Keiretsu",
    },
    {
      title: "Zaibatsu",
      source: "Wikipedia",
      description: "History and influence of Japanese Zaibatsu conglomerates before and after the war.",
      link: "https://en.wikipedia.org/wiki/Zaibatsu",
    },
  ],
  "China": [
    {
      title: "Regulating Conglomerates in China: Evidence from an Energy Conservation Program",
      source: "American Economic Review",
      description: "Study of how energy conservation programs affected Chinese conglomerates.",
      link: "https://www.aeaweb.org/articles?id=10.1257/aer.115.4.1136",
    },
    {
      title: "An Analysis of the Political Economy of China's Enterprise Conglomerates",
      source: "Google Scholar",
      description: "Analysis of the political economy of Chinese conglomerates using the electricity reform as a case study.",
      link: "https://scholar.google.com/citations?view_op=view_citation&hl=en&user=yh4DSMYAAAAJ&citation_for_view=yh4DSMYAAAAJ:u5HHmVD_uO8C",
    },
    {
      title: "Mobile Internet Business Models in China: Vertical Hierarchies, Horizontal Conglomerates, or Business Groups",
      source: "Google Scholar",
      description: "Mobile internet business models and the role of conglomerates in China.",
      link: "https://scholar.google.com/citations?view_op=view_citation&hl=en&user=CJ3ra3YAAAAJ&citation_for_view=CJ3ra3YAAAAJ:u5HHmVD_uO8C",
    },
  ],
  "India": [
    {
      title: "How the Conglomerate is taking the Indian Economy to the next level",
      source: "Times of India",
      description: "Analysis of how conglomerates are driving growth in the Indian economy.",
      link: "https://timesofindia.indiatimes.com/blogs/voices/how-the-conglomerate-is-taking-the-indian-economy-to-the-next-level/",
    },
    {
      title: "Family-Owned Conglomerates in India: Navigating the Generational Transition",
      source: "LinkedIn",
      description: "Challenges and opportunities for family-owned conglomerates in India.",
      link: "https://www.linkedin.com/pulse/family-owned-conglomerates-india-navigating-generational-tupof",
    },
    {
      title: "Indian Conglomerates to Spend $800 Billion in 10 Years, S&P Says",
      source: "Bloomberg",
      description: "Forecast of Indian conglomerate investment over the next decade.",
      link: "https://www.bloomberg.com/news/articles/2024-10-14/indian-conglomerates-to-spend-800-billion-in-10-years-s-p-says",
    },
    {
      title: "A Study on Indian Real Estate Market and Investment in Real Estate",
      source: "ResearchGate",
      description: "Study of India's real estate market and investment trends.",
      link: "https://www.researchgate.net/publication/379750002_A_Study_on_Indian_Real_Estate_Market_and_Investment_in_Real_Estate",
    },
    {
      title: "India Residential Market Dynamics | Q4 2024 | JLL Research",
      source: "JLL Research",
      description: "Analysis of India's residential market dynamics in Q4 2024.",
      link: "https://www.jll.com/en-in/insights/market-dynamics/india-residential",
    },
  ],
  "Thailand": [
    {
      title: "The Role of Conglomerates in Thailand's Economic Development",
      source: "Asian Economic Papers",
      description: "Impact of Thai conglomerates on economic development and their transformation in the 21st century.",
      link: "https://www.mitpressjournals.org/doi/full/10.1162/asep_a_00653",
    },
    {
      title: "Real Estate Market in Thailand: Trends and Investment Opportunities",
      source: "Oxford Business Group",
      description: "Overview of Thailand's real estate market dynamics, including residential and commercial segments.",
      link: "https://oxfordbusinessgroup.com/overview/in-demand-real-estate-market-continues-expand-range-opportunities-investors",
    },
    {
      title: "Thailand's Largest Family Business Groups",
      source: "NUS Business School",
      description: "Study of Thailand's largest family business groups: structure, strategy, and challenges.",
      link: "https://bschool.nus.edu.sg/thinkbusiness/leadership/thailands-largest-family-business-groups/",
    },
    {
      title: "Sustainability Practices in Thai Conglomerates",
      source: "Emerald Insight",
      description: "Research on sustainability and corporate social responsibility in major Thai companies.",
      link: "https://www.emerald.com/insight/content/doi/10.1108/IJOEM-01-2020-0037/full/html",
    },
    {
      title: "The Impact of COVID-19 on the Thai Economy and Corporate Groups",
      source: "World Bank Blogs",
      description: "Overview of the pandemic's impact on key sectors of Thailand's economy and major business groups.",
      link: "https://blogs.worldbank.org/eastasiapacific/impact-covid-19-thai-economy",
    },
  ],
  "Singapore": [
    {
      title: "Cooling Measures and Housing Wealth: Evidence from Singapore",
      source: "arXiv",
      description: "Impact of regulatory cooling measures on housing wealth in Singapore.",
      link: "https://arxiv.org/abs/2108.11915",
    },
    {
      title: "Sea Level Rise Risks, Adaptation Strategies, and Real Estate Prices in Singapore",
      source: "Journal of Public Economics",
      description: "Climate change risks and their effect on real estate prices in Singapore.",
      link: "https://doi.org/10.1016/j.jpubeco.2023.105290",
    },
    {
      title: "Urban Housing Affordability: Policy Interventions in the Singapore Public Housing Sector",
      source: "International Real Estate Review",
      description: "Effectiveness of housing affordability policies in Singapore's public housing sector.",
      link: "https://www.um.edu.mo/fba/irer/papers/past/vol22n4/v22n4-02.pdf",
    },
    {
      title: "Graduate Real Estate Education in Singapore: What Prospective Students Look For",
      source: "Journal of Real Estate Practice and Education",
      description: "What prospective students expect from real estate education in Singapore.",
      link: "https://doi.org/10.1080/1521473X.2011.10773176",
    },
    {
      title: "Multilevel Modeling Using Spatial Processes: Application to the Singapore Housing Market",
      source: "Computational Statistics & Data Analysis",
      description: "Spatial data modelling applied to Singapore's housing market.",
      link: "https://doi.org/10.1016/j.csda.2007.05.019",
    },
  ],
  "South Korea": [
    {
      title: "The Rise of the Chaebol: A Bibliometric Analysis of Business Groups in South Korea",
      source: "arXiv",
      description: "Systematic review of research on Korean chaebols, their economic role, and academic collaboration.",
      link: "https://arxiv.org/abs/2306.08743",
    },
    {
      title: "Rethinking Risk: Why South Korea's Conglomerates are Turning Away from China",
      source: "Australian Outlook",
      description: "Analysis of South Korean conglomerates shifting strategy away from China toward other markets.",
      link: "https://www.internationalaffairs.org.au/australianoutlook/rethinking-risk-why-south-koreas-conglomerates-are-turning-away-from-china/",
    },
    {
      title: "Conglomerates' Corporate Universities: Major Engine Behind the Growth and Success of HRD in South Korea",
      source: "Google Scholar",
      description: "The role of corporate universities in human resource development within South Korean conglomerates.",
      link: "https://scholar.google.com/citations?view_op=view_citation&hl=en&user=Ki1ajlwAAAAJ&citation_for_view=Ki1ajlwAAAAJ:u5HHmVD_uO8C",
    },
    {
      title: "When Organizational Performance Matters for Personnel Decisions: Executives' Career Patterns in a Conglomerate",
      source: "Google Scholar",
      description: "How performance metrics influence personnel decisions in South Korean conglomerates.",
      link: "https://scholar.google.com/citations?view_op=view_citation&hl=en&user=ItQ_QXwAAAAJ&citation_for_view=ItQ_QXwAAAAJ:9yKSN-GCB0IC",
    },
  ],
  "Malaysia": [
    {
      title: "Does Board Diversity Matter? Evidence from Malaysian Public Listed Companies",
      source: "Journal of Contemporary Accounting & Economics",
      description: "Impact of board diversity on the financial performance of Malaysian public companies.",
      link: "https://doi.org/10.1016/j.jcae.2021.100372",
    },
    {
      title: "Determinants of Foreign Direct Investment in Malaysia: Evidence from Auto-Regressive Distributed Lag Approach",
      source: "Cogent Economics & Finance",
      description: "Factors influencing foreign direct investment inflows into Malaysia.",
      link: "https://www.tandfonline.com/doi/full/10.1080/23322039.2019.1620643",
    },
    {
      title: "Household Debt and Its Impact on Economic Growth in Malaysia",
      source: "Research in International Business and Finance",
      description: "Study of household debt structure and its effect on Malaysia's economic growth.",
      link: "https://doi.org/10.1016/j.ribaf.2020.101268",
    },
  ],
  "Indonesia": [
    {
      title: "Corporate Governance and Firm Performance in Indonesia",
      source: "Asian Journal of Business and Accounting",
      description: "Relationship between corporate governance practices and financial performance of Indonesian companies.",
      link: "https://ajbc.um.edu.my/article/view/3416",
    },
    {
      title: "The Impact of Palm Oil Production on Indonesia's Economic Growth",
      source: "Journal of Agricultural Economics",
      description: "Role of palm oil in Indonesia's GDP and socio-economic implications of the industry.",
      link: "https://doi.org/10.1111/1477-9552.12480",
    },
    {
      title: "Digital Financial Inclusion in Indonesia: From Bank Branch to Agent Network",
      source: "World Development",
      description: "Development of digital financial inclusion in Indonesia's banking sector through agent networks.",
      link: "https://doi.org/10.1016/j.worlddev.2020.104954",
    },
  ],
  "Taiwan": [
    {
      title: "Technological Innovation and TSMC's Role in Global Semiconductor Supply Chain",
      source: "Harvard Business Review",
      description: "TSMC's innovation strategy and its influence on the global semiconductor industry.",
      link: "https://hbr.org/2023/11/tsmc-semiconductor-innovation",
    },
    {
      title: "The Green Transition of Taiwan's Manufacturing Sector",
      source: "Journal of Cleaner Production",
      description: "Environmental initiatives in Taiwan's manufacturing sector.",
      link: "https://doi.org/10.1016/j.jclepro.2022.132345",
    },
    {
      title: "Digital Banking Adoption in Taiwan: Consumer Behavior and Regulatory Impacts",
      source: "Asian Journal of Innovation and Policy",
      description: "Analysis of digital banking adoption rates among Taiwanese consumers.",
      link: "https://doi.org/10.1504/AJIP.2021.10034567",
    },
  ],
  "Saudi Arabia": [
    {
      title: "Vision 2030 and Economic Diversification in Saudi Arabia",
      source: "Middle East Policy",
      description: "Assessment of Vision 2030 initiatives and their impact on Saudi Arabia's economic diversification.",
      link: "https://doi.org/10.1111/mepo.12687",
    },
    {
      title: "The Rise of Saudi Aramco: From Oil Giant to Global Energy Major",
      source: "Energy Economics",
      description: "Transformation of Saudi Aramco from an oil monopoly into a global energy conglomerate.",
      link: "https://doi.org/10.1016/j.eneco.2021.105200",
    },
    {
      title: "Tourism and Religious Pilgrimage: Economic Impact on Saudi Regions",
      source: "Tourism Management Perspectives",
      description: "Economic effects of religious pilgrimage on Saudi Arabia's regional development.",
      link: "https://doi.org/10.1016/j.tmp.2022.100919",
    },
  ],
};

const flagEmoji = (country) => ({
  "Japan": "🇯🇵", "China": "🇨🇳", "India": "🇮🇳", "Thailand": "🇹🇭",
  "Singapore": "🇸🇬", "South Korea": "🇰🇷", "Malaysia": "🇲🇾",
  "Indonesia": "🇮🇩", "Taiwan": "🇹🇼", "Saudi Arabia": "🇸🇦",
}[country] || "🌏");

const Research = () => {
  const [selectedCountry, setSelectedCountry] = useState("All");

  const filteredKeys = selectedCountry === "All" ? ALL_COUNTRIES : [selectedCountry];

  return (
    <div className="pt-32 p-6 text-white bg-black min-h-screen">
      <h1 className="text-3xl font-bold mb-6 border-b border-gray-700 pb-2">
        📚 Research Articles by Country
      </h1>

      <div className="mb-8 flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCountry("All")}
          className={`px-4 py-1 rounded-full font-semibold transition
            ${selectedCountry === "All"
              ? "bg-white text-black"
              : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}
        >
          All
        </button>
        {ALL_COUNTRIES.map((country) => (
          <button
            key={country}
            onClick={() => setSelectedCountry(country)}
            className={`px-4 py-1 rounded-full font-semibold transition
              ${selectedCountry === country
                ? "bg-white text-black"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}
          >
            <span className="mr-1">{flagEmoji(country)}</span>
            {country}
          </button>
        ))}
      </div>

      {filteredKeys.map((country) => (
        <div key={country} className="mb-10">
          <h2 className="text-2xl font-semibold mb-4 border-b border-gray-600 pb-1 flex items-center gap-3">
            <span className="text-3xl">{flagEmoji(country)}</span>
            {country}
          </h2>
          <div className="space-y-6">
            {groupedArticles[country]?.length > 0 ? (
              groupedArticles[country].map((article, index) => (
                <div
                  key={index}
                  className="border border-gray-800 rounded-xl p-4 bg-gray-900 hover:bg-gray-800 transition"
                >
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-lg font-bold text-gray-400">{index + 1}.</span>
                    <a
                      href={article.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xl font-semibold text-blue-400 hover:underline"
                    >
                      {article.title}
                    </a>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{article.source}</p>
                  <p className="mt-2 text-gray-300">{article.description}</p>
                </div>
              ))
            ) : (
              <p className="text-gray-500 italic">No articles available for {country} yet.</p>
            )}
          </div>
        </div>
      ))}

      <div className="mt-12 text-xs text-center text-gray-500 italic">
        Sources are for research only. Always check full text for up-to-date info.
      </div>
    </div>
  );
};

export default Research;
