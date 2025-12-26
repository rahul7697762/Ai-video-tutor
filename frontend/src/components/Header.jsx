import { Play, History } from 'lucide-react'

function Header({ onHistoryClick, historyCount }) {
    return (
        <header className="header">
            <div className="header-logo">
                <Play size={28} />
                <span>LearnTube AI</span>
            </div>

            <div className="header-actions">
                <button className="header-btn" onClick={onHistoryClick}>
                    <History size={18} />
                    <span>History</span>
                    {historyCount > 0 && <span className="count">{historyCount}</span>}
                </button>
            </div>
        </header>
    )
}

export default Header
