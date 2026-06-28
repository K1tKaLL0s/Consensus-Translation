Please act as a senior product designer, UX designer, and UI designer. Help me further improve the complete UI and feature design of a translation software product.

I will provide existing design versions, reference images, or existing screens. Please first analyze the current design’s feature structure, interface hierarchy, visual style, interaction flow, and weaknesses. Then systematically optimize the design based on that analysis.

You are allowed to browse the web to research the information and design references you need. Please focus on the following types of products and design systems:

1. Mainstream translation software:
   - DeepL
   - Google Translate
   - Microsoft Translator
   - Papago
   - Reverso
   - Youdao Translate
   - Tencent Translator

2. AI chat applications:
   - ChatGPT
   - Claude
   - Gemini
   - Perplexity

3. Platform design systems:
   - Windows Fluent Design
   - Android Material Design
   - Mainstream desktop SaaS software UI
   - Mainstream mobile utility app UI

Do not directly copy any existing product interface. Instead, learn from their strengths in layout, information hierarchy, interaction flow, component design, and visual style, then redesign a UI system suitable for this product.

Product positioning:
This is a translation software product designed for general users and gamers. It supports Windows desktop and Android mobile platforms. The core goal is to allow users to quickly submit text, images, or files for translation, and receive clear, reliable, and traceable translation results under different modes.

Core features include:
- Text translation
- Image translation
- File translation
- Translation history
- Translation result display
- Local Mode / AI Collaboration Mode switch
- Standard Translation Mode
- Learning Mode
- User rating feedback
- Local termbase
- Cloud termbase
- Terminology management
- API configuration
- Settings center
- Multi-level interface navigation

Please improve the UI and functionality of the following interface levels:

Level 1 screens:

1. Main interface
   - Use an overall layout similar to AI chat applications.
   - The center area should be used for translation task input and result display.
   - The input box should support typing and pasting text by default.
   - Merge “Upload File” and “Upload Image” into one circular upload button with a “+” icon in the center.
   - Remove the separate “Paste Text” entry.
   - Display translation history on the left sidebar.
   - Place the Settings entry at the bottom-left corner.
   - Provide mode-switching controls near the top area or near the input area.
   - Show clear status feedback while translation is in progress.
   - After translation is complete, display the result in a card or chat-bubble style.

2. Android main interface
   - Adapt the design to a single-column mobile layout.
   - Preserve the core translation features.
   - Remove the Learning Mode entry from the Android app.
   - Use mobile-friendly interactions such as bottom navigation, floating action buttons, or top switching bars.
   - Ensure the interface is friendly for one-handed use, with reasonable button sizes and clear information hierarchy.

Level 2 screens:

1. Translation history screen
   - Display a list of historical translation tasks.
   - Support filtering by time, file type, mode, rating, and other criteria.
   - Support searching translation history.
   - Each record should display the source language, target language, task type, time, and a brief translation result.

2. Translation detail screen
   - Display the original text, translated text, terminology matches, AI revision suggestions, user rating, and related information.
   - Support actions such as copy, export, re-translate, add to termbase, and submit rating feedback.
   - Clearly distinguish between the source text and the translated text.

3. Learning Mode screen
   - Design the Learning Mode entry and interface only for the Windows desktop version.
   - Guide the user to submit a training set first, then a validation set.
   - Provide a “Start Training” button.
   - Display training status, consensus results, conflict items, manual review entry, and training completion feedback.
   - Support Local Mode / AI Collaboration Mode switching.
   - In Learning Mode, add Manual Review Mode, Self-Iterative Mode, and Self-Decision Mode.
   - Self-Decision Mode should only be available when AI Collaboration Mode is enabled.

4. Settings screen
   - Design it as a clear settings center.
   - You may refer to the settings structures of mainstream translation software and AI software.
   - It should include at least the following sections:
     - General settings
     - Translation settings
     - Termbase settings
     - API settings
     - Data and privacy
     - Appearance settings
     - About

Level 3 screens:

1. API configuration screen
   - Enter this screen from Settings.
   - Allow users to configure APIs in the OpenAI API format.
   - Fields should include:
     - API Name
     - Base URL
     - API Key
     - Model Name
     - Enable / disable this API
     - Test connection button
     - Save button
   - Clearly remind users about API Key security.
   - Support status messages such as connection successful, connection failed, and configuration error.

2. Termbase management screen
   - Enter this screen from Settings.
   - Include:
     - Enable local termbase
     - Enable cloud termbase
     - Export termbase
     - Import termbase
     - View terms
     - Search terms
     - Edit terms
     - Delete terms
   - Each term entry should display the source term, translated term, domain, source, last updated time, and usage count.

3. Export termbase screen
   - Support selecting export formats such as CSV, JSON, and XLSX.
   - Support selecting export scope, such as all terms, current project terms, and user-confirmed terms.
   - Provide export progress and completion feedback.

4. Appearance settings screen
   - Support Light Mode, Dark Mode, and Follow System.
   - Support theme color preview.
   - Support font size and interface density settings.

5. Data and privacy screen
   - Display management options for local data, cloud data, cache, translation history, and other data.
   - Support clearing translation history, clearing cache, and exporting user data.
   - Clearly explain the data usage differences between Local Mode and AI Collaboration Mode.

Visual design requirements:
- The overall style should be modern, clean, and professional, suitable for a real product release.
- You may follow the color direction of the reference images, but the visual hierarchy must be further optimized.
- The Windows version may lean toward a desktop productivity tool style.
- The Android version may lean toward a lightweight, clear, and touch-friendly mobile app style.
- Use a unified design system, including:
  - Color system
  - Typography system
  - Corner radius system
  - Shadow system
  - Spacing system
  - Icon style
  - Button states
  - Input field states
  - Card components
  - Dialog components
  - Toast / Snackbar feedback
  - Empty states
  - Loading states
  - Error states

Interaction design requirements:
- All core actions must provide clear feedback.
- Avoid making the main interface overly complex by stacking too many features together.
- Place advanced features in secondary or tertiary screens, keeping the main interface simple.
- For features that may involve data transmission, such as AI Collaboration, API configuration, and cloud termbase, provide clear user-facing explanations.
- Learning Mode should include a clear onboarding flow for new users.
- User rating feedback should be naturally integrated into the translation result card without interrupting the user’s workflow.

Final output requirements:
Please generate complete high-fidelity UI designs, including:

1. Windows desktop version:
   - Main interface
   - Translation history screen
   - Translation detail screen
   - Learning Mode screen
   - Settings screen
   - API configuration screen
   - Termbase management screen
   - Export termbase screen
   - Data and privacy screen
   - Appearance settings screen

2. Android mobile version:
   - Main interface
   - Translation result screen
   - History screen
   - Settings screen
   - API configuration screen
   - Termbase management screen
   - Data and privacy screen

3. Component library:
   - Buttons
   - Input fields
   - Upload button
   - Mode switcher
   - Tags
   - Cards
   - Sidebar
   - Top bar
   - Bottom navigation
   - Dialogs
   - Toast / Snackbar
   - Loading states
   - Empty states
   - Error states

4. Design guidelines:
   - Color system
   - Typography system
   - Spacing system
   - Corner radius system
   - Shadow system
   - Icon guidelines
   - Responsive layout explanation

Please ensure that the functional logic between all screens is consistent, the visual style is unified, components are reusable, and layers are clearly named so the design can be easily modified and implemented later.