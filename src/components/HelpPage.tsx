import './HelpPage.css';

const HelpPage = () => {
  return (
    <div className="help-page">
      <h2>Help & Tips</h2>
      
      <div className="help-section">
        <h3>🎯 How to Get the Best Results</h3>
        <div className="tips-grid">
          <div className="tip-card">
            <h4>Be Specific</h4>
            <p>Instead of "pricing rules," try "fine amounts for incorrect price displays on retail items"</p>
          </div>
          <div className="tip-card">
            <h4>Ask for Citations</h4>
            <p>Request specific law sections: "What Mass law gives me authority to cite pricing violations?"</p>
          </div>
          <div className="tip-card">
            <h4>Context Matters</h4>
            <p>Mention the type of business: "gas station pump accuracy requirements" vs "grocery store scale rules"</p>
          </div>
          <div className="tip-card">
            <h4>Field-Ready Questions</h4>
            <p>Ask practical questions: "How do I handle a business that refuses inspection?"</p>
          </div>
        </div>
      </div>

      <div className="help-section">
        <h3>📝 Example Conversations</h3>
        
        <div className="example-conversation">
          <h4>Pricing Violations & Fines</h4>
          <div className="conversation-flow">
            <div className="user-example">
              <strong>Inspector:</strong> "What's the fine for incorrect pricing on 12 items at a retail store?"
            </div>
            <div className="ai-example">
              <strong>W&M Helper:</strong> "Under Mass. Gen. Laws Ch. 98, §§56-57, you can issue fines of $200 per violation. For 12 items, that's $2,400 total. Quote section 56A for your citation authority. The law requires that advertised prices match scanned prices, and each incorrect item constitutes a separate violation."
            </div>
          </div>
        </div>

        <div className="example-conversation">
          <h4>Scale Inspection Authority</h4>
          <div className="conversation-flow">
            <div className="user-example">
              <strong>Inspector:</strong> "A business owner is refusing to let me inspect their scales. What's my legal authority?"
            </div>
            <div className="ai-example">
              <strong>W&M Helper:</strong> "Under Mass. Gen. Laws Ch. 98, §34, you have the right to enter any premises during business hours to inspect weighing and measuring devices. Refusal to allow inspection is a violation under §57, punishable by fine. You can cite the specific statute and explain that compliance is mandatory for business operation."
            </div>
          </div>
        </div>

        <div className="example-conversation">
          <h4>Electronic Price Tags (New Regulations)</h4>
          <div className="conversation-flow">
            <div className="user-example">
              <strong>Inspector:</strong> "Store wants to use electronic price tags. What are the new Mass Means Business rules?"
            </div>
            <div className="ai-example">
              <strong>W&M Helper:</strong> "Under the recent Mass Means Business initiative, electronic price tags are permitted with restrictions: price updates only during store closure hours OR between 1:00-3:00 AM for 24-hour stores. This prevents the pricing manipulation issues you've encountered while allowing business flexibility."
            </div>
          </div>
        </div>
      </div>

      <div className="help-section">
        <h3>🔧 Features</h3>
        <div className="features-list">
          <div className="feature-item">
            <span className="feature-icon">💬</span>
            <div>
              <h4>Chat History</h4>
              <p>All your conversations are saved. Click on previous chats in the sidebar to continue where you left off.</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔄</span>
            <div>
              <h4>Context Awareness</h4>
              <p>The AI remembers your conversation history, so you can ask follow-up questions without repeating context.</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📱</span>
            <div>
              <h4>Mobile Ready</h4>
              <p>Use it on your phone during field inspections. All features work on mobile browsers.</p>
            </div>
          </div>
          <div className="feature-item">
            <span className="feature-icon">⚖️</span>
            <div>
              <h4>Legal Authority</h4>
              <p>Get specific law citations and section numbers to include in your inspection reports and citations.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="help-section">
        <h3>💡 Pro Tips from the Field</h3>
        <div className="pro-tips">
          <div className="pro-tip">
            <strong>Before Inspections:</strong> Ask about specific business types or common violations to prepare.
          </div>
          <div className="pro-tip">
            <strong>During Inspections:</strong> Take photos first, then ask about citation procedures while on-site.
          </div>
          <div className="pro-tip">
            <strong>Documentation:</strong> Request the exact legal language to include in your reports.
          </div>
          <div className="pro-tip">
            <strong>Follow-ups:</strong> Use chat history to reference previous similar cases for consistency.
          </div>
        </div>
      </div>

      <div className="help-section">
        <h3>📞 Still Need Help?</h3>
        <p>This tool was built by a working Weights & Measures inspector who understands the real challenges you face in the field. If you have suggestions for improvements or need help with specific features, feel free to reach out.</p>
      </div>
    </div>
  );
};

export default HelpPage;