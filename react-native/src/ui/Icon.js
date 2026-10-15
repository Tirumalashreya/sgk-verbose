// Line icons (DESIGN.md §7): 24-unit grid, 1.75 stroke, rounded caps.
import React from 'react';
import Svg, { Path, Circle, Rect } from 'react-native-svg';

const P = {
  mic: <><Rect x="9" y="3" width="6" height="11" rx="3" /><Path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7" /></>,
  upload: <><Path d="M12 15V4M7.5 8.5 12 4l4.5 4.5" /><Path d="M4 14v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" /></>,
  link: <><Path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2" /><Path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2" /></>,
  home: <Path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z" />,
  clock: <><Circle cx="12" cy="12" r="8.5" /><Path d="M12 7.5V12l3 2" /></>,
  search: <><Circle cx="11" cy="11" r="6.5" /><Path d="m16 16 4 4" /></>,
  back: <Path d="M15 5 8 12l7 7" />,
  chevron: <Path d="m9 5 7 7-7 7" />,
  trash: <><Path d="M4.5 7h15M10 7V4.5h4V7M6.5 7l1 12.5a1 1 0 0 0 1 .9h7a1 1 0 0 0 1-.9l1-12.5" /></>,
  share: <><Path d="M12 15V4M7.5 8.5 12 4l4.5 4.5" /><Path d="M6 12H5a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-6a1 1 0 0 0-1-1h-1" /></>,
  check: <Path d="m5 12.5 4.5 4.5L19 7.5" />,
  alert: <><Path d="M12 4 3 19.5h18z" /><Path d="M12 10v4.5M12 17.2v.1" /></>,
  stop: <Rect x="7" y="7" width="10" height="10" rx="2" />,
  book: <><Path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z" /><Path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z" /></>,
  lotus: <><Path d="M12 19c-4 0-7.5-2.5-8.5-6 2.8-.4 5.6.6 8.5 3.5 2.9-2.9 5.7-3.9 8.5-3.5-1 3.5-4.5 6-8.5 6z" /><Path d="M12 16.5c-2-2.2-2.6-5-1.6-8.5.5-1.5 1-2.6 1.6-3.5.6.9 1.1 2 1.6 3.5 1 3.5.4 6.3-1.6 8.5z" /></>,
  globe: <><Circle cx="12" cy="12" r="8.5" /><Path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5z" /></>,
  close: <Path d="M6 6l12 12M18 6 6 18" />,
};

export default function Icon({ name, size = 22, color, strokeWidth = 1.75 }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      {P[name]}
    </Svg>
  );
}
