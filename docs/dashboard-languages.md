# Dashboard languages

Use the language selector on the sign-in screen or top bar to choose Turkish, English, or Russian. The preference is saved in this browser's local storage for the current origin, survives reloads, and can change without signing out.

On small screens, the page selector provides the same role-appropriate views as the sidebar. Wide call tables scroll inside their own wrapper.

The interface locale controls navigation, system messages, form labels/placeholders, and date/number presentation. Call-history times use UTC; appointment formatting retains the application's business timezone.

Changing the language does not translate, save, or rewrite:

- The first spoken greeting, including unsaved editor text.
- Published or draft knowledge documents.
- Customer names, notes, contacts, or stored table content.
- Integration credentials and configuration values.

The voice agent reads the saved first message in its original language. Edit and save it in **Opening message** to change that text. To change business knowledge, update and publish the relevant document.

## Maintaining translations

`oim-ui/locales.js` contains the three system-message catalogs. Turkish source messages act as keys. English and Russian entries must preserve their `{0}`, `{1}`, and other interpolation fields.

`i18n.js` applies known system messages to text and label attributes without rebuilding forms. It observes new system messages and retains the original keys for later switches. It skips input values, textarea content, stored table data, and elements marked `data-user-content` or `data-i18n-ignore`.

Use `OIMI18n.t(message, parameters)` for new dynamic messages and `OIMI18n.number` / `OIMI18n.date` for locale-sensitive display. Keep customer content and credentials out of the catalog, and explicitly mark new user-content containers.

Run `pnpm test` after editing translations. The tests compare catalog coverage/interpolation fields, exercise DOM updates and language persistence, and verify that switching preserves user content and form values.

