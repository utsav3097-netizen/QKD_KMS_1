import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

// Reverted to the original, stable localhost base URL
const api = axios.create({
  baseURL: "http://localhost:8000",
});

function App() {
  const [keys, setKeys] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mockSaeId, setMockSaeId] = useState("SAE-APP-001");

  useEffect(() => {
    if (message || error) {
      const timer = setTimeout(() => {
        setMessage("");
        setError("");
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [message, error]);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      // Explicitly calling the new QKD route
      const res = await api.get("/api/v1/keys");
      setKeys(res.data);
      setError("");
    } catch (err) {
      setError("Failed to fetch keys from KMS");
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleReserve = async () => {
    setLoading(true);
    setMessage("");
    setError("");
    try {
      const res = await api.post(`/api/v1/keys/${mockSaeId}/enc_keys`);
      const reservedKeyId = res.data.keys[0].key_id;
      setMessage(`Successfully delivered key ${reservedKeyId.substring(0,8)}... to ${mockSaeId}`);
      fetchKeys();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to reserve key. Buffer might be empty.");
    }
    setLoading(false);
  };

  const handleRelease = async (id) => {
    setLoading(true);
    setMessage("");
    setError("");
    try {
      const res = await api.post(`/api/v1/keys/${id}/release`);
      setMessage(res.data.message);
      fetchKeys();
    } catch (err) {
      setError("Failed to release key");
    }
    setLoading(false);
  };

  const handleConsume = async (id) => {
    setLoading(true);
    setMessage("");
    setError("");
    try {
      const res = await api.post(`/api/v1/keys/${id}/consume`);
      setMessage(res.data.message);
      fetchKeys();
    } catch (err) {
      setError("Failed to consume key");
    }
    setLoading(false);
  };

  return (
    <div className="app-bg">
      <header className="topbar">
        <div className="brand">
          <span className="brand-badge">🔐</span>
          <h1>QKD Key Management System</h1>
        </div>
        <div className="top-actions">
          <input
            type="text"
            value={mockSaeId}
            onChange={(e) => setMockSaeId(e.target.value)}
            className="sae-input"
            title="Simulated Requesting Application ID"
          />
          <button className="btn" onClick={handleReserve} disabled={loading}>
            📡 Request Key (SAE)
          </button>
          <button className="btn btn-light" onClick={fetchKeys} disabled={loading}>
            Refresh Buffer
          </button>
        </div>
      </header>

      <div className="container">
        <div className="stats">
          <div className="chip">Keys in Buffer: {keys.length}</div>
        </div>

        {message && <div className="success-msg" style={{marginBottom: "20px"}}>{message}</div>}
        {error && <div className="error-msg" style={{marginBottom: "20px"}}>{error}</div>}

        <div className="card list-card" style={{ width: "100%", boxSizing: "border-box" }}>
          <h2>Cryptographic Key Buffer (ETSI QKD 014)</h2>
          {loading ? (
            <div className="loader">Loading...</div>
          ) : (
            <div className="scroll-x">
              <table className="product-table">
                <thead>
                  <tr>
                    <th>Key ID (UUID)</th>
                    <th>Key Material (256-bit HEX)</th>
                    <th>Target SAE</th>
                    <th>State</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((k) => (
                    <tr key={k.key_id}>
                      <td style={{ fontFamily: "monospace", fontSize: "12px" }}>{k.key_id}</td>
                      <td className="key-material" style={{ fontFamily: "monospace", fontSize: "12px" }}>
                        {k.key_material}
                      </td>
                      <td>
                        {k.slave_sae_id ? (
                          <span className="sae-name">{k.slave_sae_id}</span>
                        ) : (
                          <span className="unassigned">Unassigned</span>
                        )}
                      </td>
                      <td>
                        <span className={`key-state key-state-${k.state.toLowerCase()}`}>
                          {k.state}
                        </span>
                      </td>
                      <td>
                        <div className="row-actions">
                          {k.state === 'RESERVED' && (
                            <>
                              <button className="btn btn-release" onClick={() => handleRelease(k.key_id)}>
                                Release
                              </button>
                              <button className="btn btn-consume" onClick={() => handleConsume(k.key_id)}>
                                Consume
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {keys.length === 0 && (
                    <tr>
                      <td colSpan={5} className="empty">
                        No keys available in the buffer.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;