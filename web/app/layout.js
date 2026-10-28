import "./globals.css";

export const metadata = {
  title: "MediPower | Research-only medical information retrieval",
  description: "Experimental retrieval and facility-ranking research demo using fictional examples only. Not medical diagnosis or clinical triage."
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body><a className="skip-link" href="#main-content">Skip to research form</a>{children}</body>
    </html>
  );
}