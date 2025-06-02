//import React from 'react';
import './HelpPage.css';

interface HelpPageProps {
  onNavigateToProfile?: () => void;
}

const HelpPage = ({ onNavigateToProfile }: HelpPageProps) => {
  // Provide a fallback if onNavigateToProfile is not passed
  const handleNavigate = () => {
    if (onNavigateToProfile) {
      onNavigateToProfile();
    } else {
      window.location.hash = '#profile';
    }
  };

  return (
    <div className="help-page">
      <h2>Help & Tips</h2>
      <div className="help-section mobile-app-section">
        <h3>📱 Install Mobile App</h3>
        <div className="mobile-app-highlight">
          <div className="mobile-app-content">
            <h4>Get Instant Field Access</h4>
            <p>Install W&M Helper as an app on your phone for lightning-fast access during inspections. No more hunting for bookmarks or typing URLs while standing in a store.</p>
            <div className="mobile-benefits">
              <div className="benefit-item">
                <span className="benefit-icon">⚡</span>
                <span>One-tap access from home screen</span>
              </div>
              <div className="benefit-item">
                <span className="benefit-icon">📵</span>
                <span>Works offline after initial load</span>
              </div>
              <div className="benefit-item">
                <span className="benefit-icon">🖥️</span>
                <span>Full-screen experience (no browser bars)</span>
              </div>
              <div className="benefit-item">
                <span className="benefit-icon">🔒</span>
                <span>Secure and private on your device</span>
              </div>
            </div>
            <button className="install-guide-button" onClick={handleNavigate}>
              Go to Profile → Install App
            </button>
            <div className="install-preview">
              <p><strong>What you'll see:</strong> In your Profile page, you'll find an "Install App" section with either a one-click install button or step-by-step instructions for your device.</p>
            </div>
          </div>
        </div>
      </div>
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
              <strong>Inspector:</strong> "can you tell me about price verification and fees and charges for failure as well?"
            </div>
            <div className="ai-example">
              <strong>W&M Helper:</strong> "Based on the provided regulations, here are the key points about price verification, fees, and charges for violations: Price Verification Requirements: - All pricing must be clear and conspicuous to consumers - If there is a discrepancy between advertised price, sticker price, scanner price, display price and checkout price, the lowest price must be charged - All prices represented to consumers for the same item must be consistent - Stores must provide itemized sales receipts showing prices charged Inspections & Violations: - The Division and local officials inspect stores at least once every 24 months for stores with 3+ registers - Can inspect more frequently based on consumer complaints or previous violations - Sample size for accuracy tests is 50-200 items - Scanner accuracy must be at least 98% - Each scanning error constitutes a separate violation Fees & Penalties: For Scanner System Stores: - $200 per violation up to $5,000 maximum per inspection - $300 per loyalty card price violation up to $5,000 maximum - $1,000 fine for insufficient number of scanners Price Discrepancy Penalties: If scanner/checkout price is higher than lowest advertised/displayed price: - Item priced $10 or less: Free to customer - Item priced over $10: Customer pays lowest price minus $10 - Additional identical items: Customer pays lowest price Progressive Fines: - First failed inspection: $200 civil fine - Second failed inspection: $500 civil fine - Subsequent failed inspections: $1,000 civil fine Enforcement: - Fines must be paid within 21 days unless appealed - Violations must be corrected immediately upon notice - Repeat/intentional violations can result in loss of exemptions for 12 months - Cases may be referred to Attorney General for enforcement The regulations aim to ensure pricing accuracy and transparency while providing meaningful penalties for violations. The fine structure increases for repeat offenders and there are additional penalties for loyalty card price discrepancies."
            </div>
            <div className="user-example">
              <strong>Inspector:</strong> "So if i went to one and they failed 2 and i didn't do either fine there was 11 errors 5 against the customer on the 2nd one so i did a civil citation for 1000 (200x5) should i have given them a 500 dollar fine as well?"
            </div>
            <div className="ai-example">
              <strong>W&M Helper:</strong> "Based on 202 CMR 7.11(5), for automated retail checkout system inspections: - First failed inspection = $200 civil fine - Second failed inspection = $500 civil fine - Subsequent failed inspections = $1,000 civil fine If this was their second failed inspection, you should have issued both: 1. The $500 civil fine for the second failed inspection, AND 2. The $1,000 civil fine for the 5 overcharge violations ($200 x 5) So in this case, the total fines should have been $1,500 ($500 + $1,000). The $500 fine is mandatory for a second failed inspection under 7.11(5), while the overcharge violations are calculated separately at $200 per violation up to the maximum cap of $2,500 per inspection under 7.11(9). So yes, you should have included the $500 fine for it being their second failed inspection in addition to the $1,000 in overcharge violation fines."
            </div>
          </div>
        </div>
        <div className="example-conversation">
          <h4>Scale Inspection Authority</h4>
          <div className="conversation-flow">
            <div className="user-example">
              <strong>Inspector:</strong> "Good Morning, I went to go inspect the scales at a fish house and they won't let me"
            </div>
            <div className="ai-example">
              <strong>W&M Helper:</strong> "Good morning! This is a situation you have clear authority to address under Massachusetts weights and measures law. Here's what you need to know: ## Your Legal Authority Under **M.G.L. c. 98, § 32**, you have the authority to inspect weighing and measuring devices used for buying, selling or exchanging goods, and if found inaccurate, you shall inform the mayor or selectmen to cause the law to be enforced. More specifically, **M.G.L. c. 98, § 52** gives you the right to: - Enter premises where weighing devices are kept or used - Examine weighing and measuring devices - Test and mark them according to results ## Fish-Specific Authority Since this is a fish house, you also have authority under **M.G.L. c. 94, § 86**, which requires that "all fish when landed from a vessel or boat shall be weighed by a public weigher of fish" when requested, and gives the director authority to adopt regulations for weighing, sorting and culling of fish. ## Next Steps 1. **Inform them of your legal authority** - Reference M.G.L. c. 98, §§ 32 and 52 2. **Document the refusal** - Note date, time, who refused, and circumstances 3. **Contact your supervisor** or the Division of Standards if they continue to refuse 4. **Consider enforcement action** - Whoever hinders, obstructs or interferes with you in performance of official duties can be punished by fine up to $500 (first offense) or $1,000 (subsequent offense) under M.G.L. c. 98, § 34 Would you like me to help you draft a formal notice to present to them, or do you need guidance on any other aspect of this situation?"
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
      <div className="help-section disclaimer-section">
        <h3>⚠️ Important Legal Disclaimer</h3>
        <div className="legal-disclaimer">
          <div className="disclaimer-content">
            <h4>Use Responsibly - AI Can Make Mistakes</h4>
            <p>This AI assistant is a <strong>research tool</strong>, not a substitute for official legal guidance or your professional judgment. Here's what you need to know:</p>
            <div className="disclaimer-grid">
              <div className="disclaimer-item">
                <span className="disclaimer-icon">🔍</span>
                <div>
                  <strong>Always Verify</strong>
                  <p>Cross-check AI responses with official Mass.gov sources, current regulations, and your department's guidance before taking enforcement action.</p>
                </div>
              </div>
              <div className="disclaimer-item">
                <span className="disclaimer-icon">⚖️</span>
                <div>
                  <strong>Your Professional Responsibility</strong>
                  <p>You remain fully responsible for all enforcement decisions, citations, and legal interpretations. The AI is an aid, not a replacement for your expertise.</p>
                </div>
              </div>
              <div className="disclaimer-item">
                <span className="disclaimer-icon">🤖</span>
                <div>
                  <strong>AI Limitations</strong>
                  <p>AI can hallucinate, misinterpret context, or provide outdated information. When in doubt, consult official sources or legal counsel.</p>
                </div>
              </div>
              <div className="disclaimer-item">
                <span className="disclaimer-icon">📋</span>
                <div>
                  <strong>Documentation</strong>
                  <p>Keep records of your verification process. Don't rely solely on AI output for citation justification.</p>
                </div>
              </div>
            </div>
            <div className="liability-notice">
              <p><strong>No Liability:</strong> The creators of this tool assume no responsibility for enforcement actions, legal outcomes, or decisions made based on AI responses. Use at your own professional discretion.</p>
            </div>
          </div>
        </div>
      </div>
      <div className="help-section support-section">
        <h3>📞 Still Need Help?</h3>
        <p>This tool was built by a working Weights & Measures inspector who understands the real challenges you face in the field. If you have suggestions for improvements or need help with specific features, <a href="mailto:joe@thinkpack.ai?subject=W&M Helper Support Request" className="contact-link">feel free to reach out</a>.</p>
      </div>
    </div>
  );
};

export default HelpPage;