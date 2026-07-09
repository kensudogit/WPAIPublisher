<?php
/**
 * Hero Section Block - Server-side render
 *
 * @var array    $attributes Block attributes.
 * @var string   $content    Block content.
 * @var WP_Block $block      Block instance.
 */

defined('ABSPATH') || exit;
?>
<section <?php echo get_block_wrapper_attributes(['class' => 'hero']); ?> id="hero">
	<div class="hero__inner">
		<h1 class="hero__title"><?php esc_html_e('Welcome to Our Site', 'custom-theme'); ?></h1>
		<p class="hero__subtitle"><?php esc_html_e('Build something amazing with WordPress', 'custom-theme'); ?></p>
		<a href="#contact" class="hero__cta"><?php esc_html_e('Get Started', 'custom-theme'); ?></a>
	</div>
</section>
