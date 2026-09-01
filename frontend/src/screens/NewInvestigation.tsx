import React, { useState } from 'react';
import { Button, Card } from '../components/BaseComponents';
import './NewInvestigation.css';

interface NewInvestigationProps {
  onSubmit: (walletAddress: string) => void;
  isLoading?: boolean;
}

export const NewInvestigation: React.FC<NewInvestigationProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const [walletAddress, setWalletAddress] = useState('');
  const [error, setError] = useState('');

  const isValidAddress = (address: string) => {
    // Basic Ethereum address validation
    return /^0x[a-fA-F0-9]{40}$/.test(address);
  };

  const handleChange = (value: string) => {
    setWalletAddress(value);
    if (error) setError('');
  };

  const handleSubmit = () => {
    const trimmed = walletAddress.trim();

    if (!trimmed) {
      setError('Wallet address is required');
      return;
    }

    if (!isValidAddress(trimmed)) {
      setError('Invalid wallet address. Expected 42-character Ethereum address (0x...)');
      return;
    }

    onSubmit(trimmed);
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      handleChange(text.trim());
    } catch (err) {
      setError('Could not access clipboard');
    }
  };

  return (
    <div className="new-investigation">
      <Card className="new-investigation__card">
        <h1 className="new-investigation__title">Start a New Investigation</h1>

        <div className="new-investigation__form">
          <div className="new-investigation__field">
            <label htmlFor="wallet" className="new-investigation__label">
              Wallet Address
            </label>
            <div className="new-investigation__input-group">
              <input
                id="wallet"
                type="text"
                placeholder="0x..."
                value={walletAddress}
                onChange={(e) => handleChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                className={`new-investigation__input monospace ${
                  error ? 'new-investigation__input--error' : ''
                }`}
                disabled={isLoading}
              />
              <button
                className="new-investigation__paste-btn"
                onClick={handlePaste}
                disabled={isLoading}
                title="Paste from clipboard"
              >
                📋
              </button>
            </div>
            {error && (
              <div className="new-investigation__error">{error}</div>
            )}
            <p className="new-investigation__help">
              Enter a valid Ethereum wallet address (0x followed by 40 hex characters)
            </p>
          </div>

          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={isLoading || !walletAddress.trim()}
            className="new-investigation__submit"
          >
            {isLoading ? 'Starting Investigation...' : 'Start Investigation'}
          </Button>
        </div>

        {isLoading && (
          <div className="new-investigation__progress">
            <div className="new-investigation__progress-bar">
              <div className="new-investigation__progress-fill" />
            </div>
            <p className="new-investigation__progress-text">
              Initializing investigation... This may take a moment.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
};
