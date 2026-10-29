import "./globals.css";

export const metadata = {
  title: "MediPower | Explainable AI Research Demo",
  description: "Explore fictional symptom scenarios, experimental information retrieval, and transparent facility ranking proxies. Research only — not diagnosis or medical advice.",
  applicationName: "MediPower Research Lab",
  robots: { index: true, follow: true },
  openGraph: {
    title: "MediPower | Explainable AI Research Demo",
    description: "A non-clinical, fictional-scenario research workspace for explainable retrieval and transparent ranking.",
    type: "website",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to MediPower research demo</a>
        {children}
      </body>
    </html>
  );
}
