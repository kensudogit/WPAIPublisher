#!/usr/bin/env bash
# ローカルステージング初期化（Docker WordPress）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
THEME_DIR="$ROOT_DIR/staging/wp-content/themes/custom-theme"

mkdir -p "$THEME_DIR/blocks"

if [[ ! -f "$THEME_DIR/style.css" ]]; then
  cat > "$THEME_DIR/style.css" <<'EOF'
/*
Theme Name: Custom Theme
Theme URI: https://example.com
Description: WPAIPublisher local staging theme
Author: WPAIPublisher
Version: 1.0.0
Requires at least: 6.0
Text Domain: custom-theme
*/
EOF
fi

if [[ ! -f "$THEME_DIR/index.php" ]]; then
  cat > "$THEME_DIR/index.php" <<'EOF'
<?php
defined('ABSPATH') || exit;
get_header();
?>
<main>
  <?php if (have_posts()) : while (have_posts()) : the_post(); the_content(); endwhile; endif; ?>
</main>
<?php get_footer(); ?>
EOF
fi

if [[ ! -f "$THEME_DIR/functions.php" ]]; then
  cat > "$THEME_DIR/functions.php" <<'EOF'
<?php
defined('ABSPATH') || exit;

add_action('init', function () {
    $blocks_dir = get_template_directory() . '/blocks';
    if (!is_dir($blocks_dir)) {
        return;
    }
    foreach (glob($blocks_dir . '/*/block.json') as $block_json) {
        register_block_type(dirname($block_json));
    }
});

add_action('after_setup_theme', function () {
    add_theme_support('wp-block-styles');
    add_theme_support('align-wide');
});
EOF
fi

if [[ ! -f "$THEME_DIR/header.php" ]]; then
  cat > "$THEME_DIR/header.php" <<'EOF'
<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
  <meta charset="<?php bloginfo('charset'); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
EOF
fi

if [[ ! -f "$THEME_DIR/footer.php" ]]; then
  cat > "$THEME_DIR/footer.php" <<'EOF'
<?php wp_footer(); ?>
</body>
</html>
EOF
fi

echo "Theme scaffold ready: $THEME_DIR"
