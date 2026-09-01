import React, { ReactNode } from 'react';
import './BaseComponents.css';

/* Button Component */
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}) => {
  return (
    <button
      className={`btn btn--${variant} btn--${size} ${className}`}
      {...props}
    />
  );
};

/* Badge Component */
interface BadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'neutral' | 'primary';
  children: ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  className = '',
}) => {
  return (
    <span className={`badge badge--${variant} ${className}`}>
      {children}
    </span>
  );
};

/* Card Component */
interface CardProps {
  children: ReactNode;
  className?: string;
  bordered?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  bordered = true,
}) => {
  return (
    <div className={`card ${bordered ? 'card--bordered' : ''} ${className}`}>
      {children}
    </div>
  );
};

/* Metric Card Component */
interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: { value: number; type: 'positive' | 'negative' };
  icon?: ReactNode;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  delta,
  icon,
  className = '',
}) => {
  return (
    <Card className={`metric-card ${className}`}>
      <div className="metric-card__header">
        {icon && <div className="metric-card__icon">{icon}</div>}
        <label className="metric-card__label">{label}</label>
      </div>
      <div className="metric-card__value">{value}</div>
      {delta && (
        <div className={`metric-card__delta metric-card__delta--${delta.type}`}>
          {delta.type === 'positive' ? '+' : '-'}{delta.value}
        </div>
      )}
    </Card>
  );
};

/* Risk Score Display */
interface RiskDisplayProps {
  score: number;
  label: string;
  className?: string;
}

export const RiskDisplay: React.FC<RiskDisplayProps> = ({
  score,
  label,
  className = '',
}) => {
  const getRiskColor = (score: number) => {
    if (score < 50) return '#3dd68c';
    if (score < 80) return '#f0b429';
    return '#f0473e';
  };

  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className={`risk-display ${className}`}>
      <div className="risk-display__circle">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r="45"
            fill="none"
            stroke="var(--surface-3)"
            strokeWidth="8"
          />
          <circle
            cx="60"
            cy="60"
            r="45"
            fill="none"
            stroke={getRiskColor(score)}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 300ms ease' }}
            transform="rotate(-90 60 60)"
          />
          <text
            x="60"
            y="60"
            textAnchor="middle"
            dominantBaseline="middle"
            className="risk-display__numeral"
          >
            {score}
          </text>
        </svg>
      </div>
      <div className="risk-display__label">{label}</div>
    </div>
  );
};

/* Confidence Badge with Label */
interface ConfidenceProps {
  confidence: number;
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceProps> = ({
  confidence,
  className = '',
}) => {
  const getLabel = (conf: number) => {
    if (conf < 0.4) return 'Low Confidence';
    if (conf < 0.7) return 'Moderate Confidence';
    return 'High Confidence';
  };

  const getVariant = (conf: number) => {
    if (conf < 0.4) return 'warning';
    if (conf < 0.7) return 'neutral';
    return 'success';
  };

  return (
    <Badge variant={getVariant(confidence)} className={className}>
      {Math.round(confidence * 100)}% {getLabel(confidence)}
    </Badge>
  );
};

/* AI Interpretation Panel */
interface AIInterpretationProps {
  children: ReactNode;
  className?: string;
}

export const AIInterpretationPanel: React.FC<AIInterpretationProps> = ({
  children,
  className = '',
}) => {
  return (
    <div className={`ai-panel ${className}`}>
      <div className="ai-panel__header">
        <div className="ai-panel__label">AI Interpretation</div>
      </div>
      <div className="ai-panel__content">{children}</div>
    </div>
  );
};

/* Drawer Component */
interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  className = '',
}) => {
  if (!isOpen) return null;

  return (
    <>
      <div
        className="drawer-overlay"
        onClick={onClose}
        role="presentation"
      />
      <div className={`drawer ${className}`}>
        {title && (
          <div className="drawer__header">
            <h3>{title}</h3>
            <button
              className="drawer__close"
              onClick={onClose}
              aria-label="Close drawer"
            >
              ✕
            </button>
          </div>
        )}
        <div className="drawer__content">{children}</div>
      </div>
    </>
  );
};

/* Evidence Card */
interface EvidenceCardProps {
  source: string;
  excerpt: string;
  link?: string;
  className?: string;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  source,
  excerpt,
  link,
  className = '',
}) => {
  return (
    <Card className={`evidence-card ${className}`}>
      <div className="evidence-card__source monospace">{source}</div>
      <div className="evidence-card__excerpt">{excerpt}</div>
      {link && (
        <a href={link} className="evidence-card__link">
          View →
        </a>
      )}
    </Card>
  );
};

/* Empty State */
interface EmptyStateProps {
  icon?: ReactNode;
  heading: string;
  description: string;
  action?: { label: string; onClick: () => void };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  heading,
  description,
  action,
  className = '',
}) => {
  return (
    <div className={`empty-state ${className}`}>
      {icon && <div className="empty-state__icon">{icon}</div>}
      <h3 className="empty-state__heading">{heading}</h3>
      <p className="empty-state__description">{description}</p>
      {action && (
        <Button onClick={action.onClick} variant="primary" size="md">
          {action.label}
        </Button>
      )}
    </div>
  );
};

/* Skeleton Loader */
export const SkeletonLoader: React.FC<{ rows?: number; className?: string }> =
  ({ rows = 8, className = '' }) => {
    return (
      <div className={`skeleton-loader ${className}`}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={`skeleton-row-${i}`} className="skeleton-loader__row" />
        ))}
      </div>
    );
  };

/* Status Indicator */
interface StatusIndicatorProps {
  status: 'connecting' | 'connected' | 'disconnected';
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status }) => {
  const getColor = () => {
    switch (status) {
      case 'connected':
        return 'var(--success)';
      case 'connecting':
        return 'var(--warning)';
      case 'disconnected':
        return 'var(--danger)';
    }
  };

  const getLabel = () => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting';
      case 'disconnected':
        return 'Disconnected';
    }
  };

  return (
    <div className="status-indicator">
      <span
        className="status-indicator__dot"
        style={{ backgroundColor: getColor() }}
      />
      <span className="status-indicator__label">{getLabel()}</span>
    </div>
  );
};
