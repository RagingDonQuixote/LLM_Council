import { useState } from 'react';
import './Stage4.css';

export default function Stage4({ 
  humanFeedback, 
  setHumanFeedback, 
  onSubmit, 
  isLoading,
  onCancel 
}) {
  const [continueDiscussion, setContinueDiscussion] = useState(false);

  return (
    <div className="stage stage4">
      <h3 className="stage-title">Stage 4: Human Chairman Review</h3>
      <p>Review the council's analysis above and provide your feedback:</p>
      
      <div className="human-input-section">
        <textarea
          value={humanFeedback}
          onChange={(e) => setHumanFeedback(e.target.value)}
          placeholder="Enter your feedback, comments, or instructions..."
          rows={6}
          className="feedback-textarea"
        />
        
        <div className="feedback-controls">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={continueDiscussion}
              onChange={(e) => setContinueDiscussion(e.target.checked)}
            />
            Continue discussion (rerun council with feedback)
          </label>
          
          <div className="feedback-buttons">
            <button 
              onClick={() => onSubmit(continueDiscussion)} 
              disabled={isLoading}
              className="btn btn-primary"
            >
              {isLoading ? 'Processing...' : (continueDiscussion ? 'Continue Discussion' : 'End Session')}
            </button>
            <button 
              onClick={onCancel}
              disabled={isLoading}
              className="btn btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}