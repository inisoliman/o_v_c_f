"""محلل الفيديوهات الذكي"""
import re
import logging

logger = logging.getLogger(__name__)

class VideoAnalyzer:
    SEASON_EPISODE_PATTERNS = [
        r'[Ss](\d+)[Ee](\d+)',
        r'الموسم\s*(\d+).*الحلقة\s*(\d+)',
        r'موسم\s*(\d+).*حلقة\s*(\d+)',
    ]
    
    QUALITY_PATTERNS = [r'(\d{3,4})[pP]', r'(4K|UHD|HD|SD)']
    LANGUAGE_PATTERNS = [r'(مترجم|مدبلج|عربي|إنجليزي)']
    
    def analyze_text(self, text: str) -> dict:
        result = {}
        
        # البحث عن الموسم والحلقة
        for pattern in self.SEASON_EPISODE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['season'] = int(match.group(1))
                result['episode'] = int(match.group(2))
                break
        
        # البحث عن الجودة
        for pattern in self.QUALITY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['quality'] = match.group(1)
                break
                
        # البحث عن اللغة
        for pattern in self.LANGUAGE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['language'] = match.group(1)
                break
        
        return result