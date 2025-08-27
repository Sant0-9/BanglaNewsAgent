# KhoborAgent UI

A Next.js 14 chat interface for the KhoborAgent multi-intent news and information system.

## Features

- 🤖 **Multi-Intent Chat**: Supports news, weather, markets, sports, and lookup queries
- 🌍 **Multilingual**: Primary support for Bangla with English fallback
- 🎨 **Modern UI**: Built with shadcn/ui, Tailwind CSS, and Framer Motion
- 🔄 **Real-time**: Live chat interface with typing indicators
- 📱 **Responsive**: Works perfectly on desktop, tablet, and mobile
- 🎯 **Intent Routing**: Visual feedback showing which intent was detected
- 📊 **Source Attribution**: Shows sources and confidence scores for responses

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS with custom KhoborAgent theme
- **UI Components**: shadcn/ui with Radix UI primitives
- **Icons**: Lucide React
- **Fonts**: Geist Sans & Geist Mono
- **Animations**: Framer Motion
- **State Management**: React hooks with SWR for data fetching
- **Types**: Full TypeScript support

## Getting Started

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.local.example .env.local
   ```
   Configure `API_BASE_URL` to point to your Python API (default: http://localhost:8000)

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
apps/web/
├── src/
│   ├── app/                # Next.js app router
│   │   ├── api/           # API routes (proxy to Python backend)
│   │   ├── globals.css    # Global styles and theme
│   │   ├── layout.tsx     # Root layout
│   │   └── page.tsx       # Main chat interface
│   ├── components/
│   │   └── ui/           # shadcn/ui components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utilities and configurations
│   └── types/            # TypeScript type definitions
├── package.json
├── tailwind.config.ts    # Tailwind configuration
├── tsconfig.json         # TypeScript configuration
└── components.json       # shadcn/ui configuration
```

## Theme

The app uses a custom dark theme with:
- **Background**: Deep navy (#090826) with subtle gradient and noise texture
- **Accent**: Warm gold (#d3b673) for highlights and branding
- **Typography**: Geist font family for optimal readability
- **Components**: Glass morphism effects with subtle animations

## API Integration

The frontend communicates with the Python FastAPI backend through:
- **Proxy Route**: `/api/ask` - Forwards requests to the Python API
- **Type Safety**: Full TypeScript interfaces for API requests/responses
- **Error Handling**: Graceful error handling with user-friendly messages
- **Loading States**: Visual feedback during API calls

## Commands

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Test Plan

### Prerequisites

1. **Start the backend**:
   ```bash
   cd ../../api
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend**:
   ```bash
   pnpm dev
   ```

3. Open [http://localhost:3000](http://localhost:3000)

### Test Scenarios

#### 1. Basic News Query
**Input**: "What's the latest on semiconductor export controls?"

**Expected**:
- ✅ Bangla answer with inline citations `[1]`, `[2]`, etc.
- ✅ 3+ sources shown in collapsible section
- ✅ "Routed: news" displayed with confidence score
- ✅ Confidence badge (High/Medium/Low) in top-right

#### 2. Deep Dive Functionality
**Steps**:
1. Complete a news query as above
2. Click "Deep Dive" button

**Expected**:
- ✅ Longer, more detailed answer
- ✅ Citations and sources remain intact
- ✅ Same intent routing preserved

#### 3. Timeline Feature
**Steps**:
1. Complete a news query
2. Click "Timeline" button

**Expected**:
- ✅ Modal opens showing date buckets (7 days)
- ✅ Each date shows count and top 5 headlines
- ✅ Graceful fallback if timeline API not implemented

#### 4. Language Toggle
**Steps**:
1. Complete any query in Bangla
2. Click "English" button

**Expected**:
- ✅ Immediate English translation OR
- ✅ Re-queries for English answer
- ✅ Maintains same sources and confidence

#### 5. Multi-Intent Routing
**Test different query types**:

- **Weather**: "আজকে ঢাকায় আবহাওয়া কেমন?" → "Routed: weather"
- **Markets**: "NVIDIA stock price today" → "Routed: markets" 
- **Sports**: "Bangladesh cricket latest score" → "Routed: sports"
- **Lookup**: "What is quantum computing?" → "Routed: lookup"

**Expected**:
- ✅ Correct intent detection and routing
- ✅ Toast notification if handler not yet implemented
- ✅ Visual intent badge with confidence

#### 6. Error Handling
**Test backend connectivity**:

1. Start a query, then kill the backend mid-stream
2. Try querying with backend offline

**Expected**:
- ✅ Retry toast appears when backend disconnects
- ✅ User can cancel ongoing requests
- ✅ Graceful error messages for failed requests
- ✅ No crashes or infinite loading states

#### 7. UI/UX Features
**Streaming & Loading**:
- ✅ Loading skeleton with shimmer effect while waiting
- ✅ Smooth text streaming with typing cursor
- ✅ No flicker during text updates

**Responsive Design**:
- ✅ Works on mobile, tablet, and desktop
- ✅ Chat bubbles adapt to screen size
- ✅ Header collapses properly on mobile

**Theme & Accessibility**:
- ✅ Dark theme consistent throughout
- ✅ Theme toggle works (light/dark)
- ✅ Proper focus indicators and ARIA labels

### Expected Performance
- Initial page load: < 2s
- Query response start: < 1s  
- Full response streaming: < 10s
- UI interactions: < 100ms

## Customization

The theme can be customized by modifying:
- `tailwind.config.ts` - Colors, spacing, animations
- `src/app/globals.css` - CSS custom properties and global styles
- `components.json` - shadcn/ui component configuration