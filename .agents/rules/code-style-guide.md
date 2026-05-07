---
trigger: always_on
---

# React Project Rules

## Stack
- React + Vite
- JavaScript (.js/.jsx)
- React Router
- TailwindCSS
- Axios

## Folder Structure

src/
  components/
  pages/
  layouts/
  router/
  hooks/
  services/
  utils/
  assets/

## Components

- Create reusable components.
- One component per file.
- Use PascalCase for component names.
- Use camelCase for functions and variables.

## Pages

- Keep page files focused on layout and flow.
- Move reusable logic into hooks or services.

## API

- All API calls must be inside services/.
- Never call APIs directly inside UI components.
- Use axios instance for API requests.

## Styling

- Use TailwindCSS.
- Use large touch-friendly UI elements.
- Use responsive layouts.
- Optimize for kiosk/touchscreen usage.

## Kiosk UI Rules

- Large buttons
- Large readable text
- Minimal UI clutter
- High contrast colors
- Fullscreen-friendly layout
- Easy navigation
- Avoid tiny clickable areas

## Performance

- Lazy load pages when possible.
- Avoid unnecessary state updates.
- Optimize renders.

## Code Style

- Prefer const over let.
- Avoid var.
- Use early returns.
- Keep functions short.
- Add comments only when necessary.

## Security

- Never expose secrets in frontend.
- Store API endpoints in .env.
- Validate all user inputs.

## Error Handling

- Always handle loading states.
- Always handle API errors.
- Show user-friendly error messages.