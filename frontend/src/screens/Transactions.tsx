import React, { useState } from 'react';
import { Search, Filter, Download, ChevronDown } from 'lucide-react';
import { Button, Badge, Drawer, Card } from '../components/BaseComponents';
import './Transactions.css';

interface Transaction {
  tx_hash: string;
  from: string;
  to: string;
  value: string;
  token?: string | null;
  timestamp: string;
  block?: number | null;
  risk?: 'low' | 'medium' | 'high';
}

interface TransactionsProps {
  transactions: Transaction[];
  onSelectTransaction?: (tx: Transaction) => void;
}

export const Transactions: React.FC<TransactionsProps> = ({
  transactions,
  onSelectTransaction,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<'all' | 'low' | 'medium' | 'high'>('all');
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);

  const filteredTransactions = transactions.filter((tx) => {
    const matchesSearch =
      !searchTerm ||
      tx.tx_hash.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.from.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.to.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesRisk = riskFilter === 'all' || tx.risk === riskFilter;

    return matchesSearch && matchesRisk;
  });

  const handleSelectTx = (tx: Transaction) => {
    setSelectedTx(tx);
    onSelectTransaction?.(tx);
  };

  return (
    <div className="transactions">
      {/* Toolbar */}
      <div className="transactions__toolbar">
        <div className="transactions__search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search by hash, wallet, or address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="transactions__filters">
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value as any)}
            className="transactions__filter-select"
          >
            <option value="all">All Risk Levels</option>
            <option value="low">Low Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="high">High Risk</option>
          </select>
        </div>

        <Button variant="secondary" size="sm">
          <Filter size={16} />
          More Filters
        </Button>

        <Button variant="ghost" size="sm">
          <Download size={16} />
        </Button>
      </div>

      {/* Table */}
      <Card className="transactions__card">
        {filteredTransactions.length > 0 ? (
          <div className="transactions__table">
            <div className="transactions__header">
              <div className="transactions__col-timestamp">Timestamp</div>
              <div className="transactions__col-from">From</div>
              <div className="transactions__col-to">To</div>
              <div className="transactions__col-asset">Asset</div>
              <div className="transactions__col-value">Value</div>
              <div className="transactions__col-risk">Risk</div>
              <div className="transactions__col-status">Status</div>
            </div>

            {filteredTransactions.map((tx, idx) => (
              <div
                key={`${tx.tx_hash}-${idx}`}
                className={`transactions__row ${tx.risk === 'high' ? 'transactions__row--high-risk' : ''}`}
                onClick={() => handleSelectTx(tx)}
              >
                <div className="transactions__col-timestamp">
                  <span className="transactions__time">
                    {new Date(tx.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="transactions__date">
                    {new Date(tx.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <div className="transactions__col-from">
                  <code className="monospace">
                    {tx.from.slice(0, 8)}...{tx.from.slice(-6)}
                  </code>
                </div>
                <div className="transactions__col-to">
                  <code className="monospace">
                    {tx.to.slice(0, 8)}...{tx.to.slice(-6)}
                  </code>
                </div>
                <div className="transactions__col-asset">{tx.token || 'ETH'}</div>
                <div className="transactions__col-value">{tx.value}</div>
                <div className="transactions__col-risk">
                  <Badge
                    variant={
                      tx.risk === 'high'
                        ? 'danger'
                        : tx.risk === 'medium'
                          ? 'warning'
                          : 'success'
                    }
                  >
                    {tx.risk?.toUpperCase() || 'UNKNOWN'}
                  </Badge>
                </div>
                <div className="transactions__col-status">
                  <span className="transactions__status-dot" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="transactions__empty">
            <p>No transactions found for the current filters.</p>
            <Button variant="secondary" size="sm" onClick={() => setRiskFilter('all')}>
              Clear Filters
            </Button>
          </div>
        )}
      </Card>

      {/* Detail Drawer */}
      <Drawer
        isOpen={selectedTx !== null}
        onClose={() => setSelectedTx(null)}
        title="Transaction Details"
      >
        {selectedTx && (
          <div className="transactions__detail">
            <div className="transactions__detail-section">
              <h4>Transaction Hash</h4>
              <code className="monospace transactions__detail-value">
                {selectedTx.tx_hash}
              </code>
              <button className="transactions__copy-btn">Copy</button>
            </div>

            <div className="transactions__detail-section">
              <h4>From</h4>
              <code className="monospace transactions__detail-value">
                {selectedTx.from}
              </code>
            </div>

            <div className="transactions__detail-section">
              <h4>To</h4>
              <code className="monospace transactions__detail-value">
                {selectedTx.to}
              </code>
            </div>

            <div className="transactions__detail-section">
              <h4>Value</h4>
              <div className="transactions__detail-value">{selectedTx.value}</div>
            </div>

            <div className="transactions__detail-section">
              <h4>Token</h4>
              <div className="transactions__detail-value">{selectedTx.token || 'ETH'}</div>
            </div>

            <div className="transactions__detail-section">
              <h4>Timestamp</h4>
              <div className="transactions__detail-value">
                {new Date(selectedTx.timestamp).toLocaleString()}
              </div>
            </div>

            {selectedTx.block && (
              <div className="transactions__detail-section">
                <h4>Block</h4>
                <div className="transactions__detail-value">{selectedTx.block}</div>
              </div>
            )}

            <div className="transactions__detail-section">
              <h4>Risk Level</h4>
              <Badge
                variant={
                  selectedTx.risk === 'high'
                    ? 'danger'
                    : selectedTx.risk === 'medium'
                      ? 'warning'
                      : 'success'
                }
              >
                {selectedTx.risk?.toUpperCase() || 'UNKNOWN'}
              </Badge>
            </div>

            <Button variant="secondary" className="transactions__detail-action">
              View on Graph
            </Button>
          </div>
        )}
      </Drawer>
    </div>
  );
};
