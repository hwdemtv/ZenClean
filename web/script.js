/**
 * ZenClean 落地页脚本
 */
(function() {
    'use strict';

    // ==================== 滚动动画 ====================
    function initScrollReveal() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale, .reveal-text, .reveal-subtext').forEach(el => {
            observer.observe(el);
        });
    }

    // ==================== 主题切换 ====================
    window.toggleTheme = function() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        
        // 同时更新 body 类名以双重保障 CSS 选择器生效
        if (next === 'light') {
            document.body.classList.add('light-mode');
        } else {
            document.body.classList.remove('light-mode');
        }
    };

    function initTheme() {
        // 同步初始状态至 HTML 属性及 Body 类名
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
        }

        const toggle = document.querySelector('.theme-toggle');
        if (toggle) {
            // 支持 HTML 中的内联 onclick="toggleTheme()"
            toggle.addEventListener('click', () => {
                // 如果内联调用未生效，则手动触发
                if (typeof window.toggleTheme === 'function') {
                    // 避免重复调用（如果 onclick 已经定义）
                }
            });
        }
    }

    // ==================== FAQ 折叠 ====================
    function initFaq() {
        document.querySelectorAll('.faq-question').forEach(btn => {
            btn.addEventListener('click', () => {
                const item = btn.parentElement;
                item.classList.toggle('active');
            });
        });
    }

    // ==================== FAQ 分类过滤 ====================
    function initFaqFilter() {
        const navBtns = document.querySelectorAll('.faq-nav-btn');
        if (navBtns.length === 0) return;

        navBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // 更新按钮状态
                navBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const category = btn.dataset.category;
                const faqItems = document.querySelectorAll('.faq-item');
                
                faqItems.forEach(item => {
                    const itemCat = item.dataset.category;
                    if (category === 'all' || itemCat === category) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        });
    }

    // ==================== 悬浮按钮 ====================
    function initFloatBtn() {
        const floatBtn = document.getElementById('floatDownload');
        if (!floatBtn) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                floatBtn.classList.add('visible');
            } else {
                floatBtn.classList.remove('visible');
            }
        });
    }

    // ==================== 下载弹窗 ====================
    window.openDownloadModal = function() {
        const modal = document.getElementById('downloadModal');
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
    };
    window.closeDownloadModal = function() {
        const modal = document.getElementById('downloadModal');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    };
    window.openDisclaimerModal = function() {
        const modal = document.getElementById('disclaimerModal');
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
    };
    window.closeDisclaimerModal = function() {
        const modal = document.getElementById('disclaimerModal');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    };
    window.openContactModal = function() {
        const modal = document.getElementById('contactModal');
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
    };
    window.closeContactModal = function() {
        const modal = document.getElementById('contactModal');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    };
    window.scrollToTop = function() {
        window.scrollTo({top: 0, behavior: 'smooth'});
    };

    // ==================== 统计数字增长 ====================
    function initCounter() {
        const counter = document.getElementById('totalStorage');
        if (!counter) return;

        const target = parseInt(counter.innerText.replace(/,/g, ''));
        const duration = 2000;
        let startTime = null;

        function animate(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            counter.innerText = Math.floor(progress * target).toLocaleString();
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                requestAnimationFrame(animate);
                observer.disconnect();
            }
        }, { threshold: 0.5 });
        observer.observe(counter);
    }

    // ==================== 初始化 ====================
    document.addEventListener('DOMContentLoaded', () => {
        initScrollReveal();
        initTheme();
        initFaq();
        initFaqFilter();
        initFloatBtn();
        initCounter();

        // 弹窗点击关闭
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                    modal.setAttribute('aria-hidden', 'true');
                }
            });
        });
    });
})();