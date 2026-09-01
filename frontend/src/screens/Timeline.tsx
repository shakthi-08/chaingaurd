import React from 'react';
import { Card } from '../components/BaseComponents';
import './Timeline.css';

interface TimelineEvent {
  id: string;
  timestamp: string;
  event: string;
  status: 'pending' | 'active' | 'complete';
  details?: string;
  link?: string;
}

interface TimelineProps {
  events: TimelineEvent[];
}

export const Timeline: React.FC<TimelineProps> = ({ events }) => {
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="timeline">
      <Card>
        <div className="timeline__list">
          {events.map((event, idx) => (
            <div
              key={event.id}
              className={`timeline__item timeline__item--${event.status}`}
            >
              <div className="timeline__line">
                <div className="timeline__dot" />
              </div>

              <div className="timeline__content">
                <div className="timeline__header">
                  <time className="timeline__time">{formatTime(event.timestamp)}</time>
                  <h4 className="timeline__event">{event.event}</h4>
                </div>
                {event.details && (
                  <p className="timeline__details">{event.details}</p>
                )}
                {event.link && (
                  <a href={event.link} className="timeline__link">
                    View →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
