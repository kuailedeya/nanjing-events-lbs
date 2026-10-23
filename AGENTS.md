# Frontend & UI/UX Guidelines (Apple HIG & Airbnb Spatial Exploration)

All frontend interfaces in this repository must strictly adhere to the Apple HIG (macOS Sonoma / iOS) and Airbnb Spatial Exploration design specifications. Do NOT use traditional admin dashboard templates (e.g. Vue-Element-Admin).

## Essential Rules:
1. **Layout**: 100% full-screen map base + suspended floating island top-left (`top-6 left-6 rounded-[22px]`) + floating acrylic drawer right (`top-6 right-6 bottom-6 w-[380px] md:w-[440px] rounded-[28px] bg-[#F5F5F7]/85 backdrop-blur-2xl border border-white/80 shadow-[0_20px_50px_rgba(0,0,0,0.1)]`).
2. **Layer Discipline**: Liquid glass (frosted acrylic) only for functional floating containers; content cards must remain solid white Apple Cards (`bg-white rounded-2xl border border-black/[0.04]`). Never put glass directly on content cards.
3. **Bento Grid Cards**: Crisp cover image (`rounded-xl overflow-hidden h-36`), overlaid category & distance tags (`font-variant-numeric: tabular-nums`), title (`font-semibold text-slate-900`), and quick-action footer.
4. **Airbnb Marker Pills**: Compact white pill with colored category dot; inverts to solid black (`bg-slate-950 text-white`) with snappy spring scale on active selection.
5. **Microcopy & Label Discipline**: Avoid unnecessary secondary labels and descriptions. Let the layout do the explaining. Avoid unnecessary supporting text, descriptive copy, and redundant UI microcopy.
6. **Color Budget**: ≤ 3% accent colors (`#007AFF`, `#34C759`, `#FF9500`, `#FF3B30`). Zero emojis, zero rainbow gradients.
7. **Real Verified Assets & Zero Hallucinated Links**: Never fabricate, guess, or hallucinate remote image links. Always use verified local cropped assets (`/covers/...`) harvested into the repository or query real APIs (Unsplash, Pexels) with live URL verification. Use local inline SVG data URIs as foolproof fallbacks to permanently prevent broken links, network timeouts, and infinite error loops.
8. **Typography & Iconography Standards**: Standardize icons exclusively on Lucide (`lucide-vue-next`) or Iconify (never hand-draw wild SVGs or use wild Unicode characters). For typography, prioritize Apple SF Pro / Google Fonts Inter for Western text, and Alibaba PuHuiTi (阿里普惠体, 100% free commercial license) for Chinese text.
9. **Detailed Specification**: See [DESIGN_SYSTEM.md](file:///E:/usage/DESIGN_SYSTEM.md) for full parameters and copy-paste Tailwind recipes.
