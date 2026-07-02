import { useState } from "react";
import { BrowserRouter, Link, Route, Routes, useNavigate } from "react-router-dom";
import { Company } from "./pages/Company";
import { Home } from "./pages/Home";

function TopBar() {
  const [ticker, setTicker] = useState("");
  const navigate = useNavigate();

  const go = () => {
    const t = ticker.trim().toUpperCase();
    if (t) {
      navigate(`/company/${t}`);
      setTicker("");
    }
  };

  return (
    <div className="topbar">
      <Link to="/" className="brand">
        DCF Dashboard
      </Link>
      <div className="search">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && go()}
          placeholder="Ticker, e.g. AAPL"
          aria-label="Ticker search"
        />
        <button onClick={go}>Value it</button>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <TopBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/company/:ticker" element={<Company />} />
      </Routes>
    </BrowserRouter>
  );
}
